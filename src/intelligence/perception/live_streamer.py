import os
import asyncio
import base64
import json
from io import BytesIO
import mss
import mss.tools
from PIL import Image
from google import genai
from google.genai import types
from typing import Callable, Optional, Dict, Any
import sounddevice as sd
import numpy as np
import queue
import threading
from loguru import logger
from microgravity.config.loader import load_config

from src.intelligence.perception.roi import ROIManager

class GeminiLiveStreamer:
    """
    Manages the continuous bidirectional WebSocket connection to the Gemini Multimodal Live API.
    Handles streaming screen frames and receiving real-time interaction predictions.
    """
    # Verified working model names for the Live API (bidiGenerateContent)
    LIVE_MODELS = [
        "gemini-2.0-flash-exp", # Standard flash for live
        "gemini-2.5-flash-native-audio-latest",
        "gemini-2.0-flash-live-001",
    ]

    def __init__(self, api_key: str = None):
        self._config = load_config()
        self.api_key = api_key or self._config.providers.gemini.api_key
        
        if not self.api_key:
            raise ValueError("Gemini API key not found in config or passed directly.")
        
        # Use v1alpha API version for bidiGenerateContent
        self.client = genai.Client(
            api_key=self.api_key,
            http_options={'api_version': 'v1alpha'}
        )
        self.model = self.LIVE_MODELS[0]
        self.session = None
        self.is_streaming = False
        self.on_response_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.screen_observer: Optional[Any] = None # Injected by Kernel
        
        # Audio configuration
        self.sample_rate = 16000
        self.audio_in_queue = queue.Queue()
        self.audio_out_queue = queue.Queue()
        self._audio_input_stream = None
        self._audio_output_stream = None
        
        self.current_roi = None # (x1, y1, x2, y2) in global pixels
        self.screen_size = (1920, 1080)
        self.debug_dir = None
        self._frame_count = 0

    async def start_session(self, system_instruction: str = None):
        """Establishes the WebSocket session and blocks until closed."""
        logger.info(f"[LiveStreamer] Attempting connection with models: {self.LIVE_MODELS}")
        
        config = {
            "response_modalities": ["AUDIO"],
        }
        if system_instruction:
            config["system_instruction"] = system_instruction

        try:
            self._setup_audio_streams()
        except Exception as e:
            logger.warning(f"[LiveStreamer] Audio hardware error: {e}")

        connected = False
        for model_name in self.LIVE_MODELS:
            self.model = model_name
            logger.info(f"[LiveStreamer] Trying model: {model_name}...")
            try:
                async with self.client.aio.live.connect(model=self.model, config=config) as session:
                    logger.info(f"[LiveStreamer] Connected with '{model_name}'")
                    connected = True
                    self.session = session
                    self.is_streaming = True
                    
                    tasks = [
                        asyncio.create_task(self._listen_for_responses()),
                    ]
                    if self._audio_input_stream:
                        tasks.append(asyncio.create_task(self._stream_audio_input_loop()))
                    
                    await asyncio.gather(*tasks)
                    break
            except asyncio.CancelledError:
                 break
            except Exception as e:
                logger.error(f"[LiveStreamer] Failed during session for {model_name}: {e}")
                continue
            finally:
                self.is_streaming = False
                self.session = None
                self._cleanup_audio()
        
        if not connected:
            logger.error("[LiveStreamer] All model fallbacks exhausted.")

    async def disconnect(self):
        self.is_streaming = False
        logger.info("[LiveStreamer] Disconnect requested.")

    def _capture_screen_compressed(self) -> bytes:
        if not self.screen_observer:
             with mss.mss() as sct:
                 monitor = sct.monitors[1]
                 self.screen_size = (monitor["width"], monitor["height"])
                 sct_img = sct.grab(monitor)
                 img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        else:
            if self.current_roi:
                x1, y1, x2, y2 = self.current_roi
                region = (x1, y1, x2 - x1, y2 - y1)
                img = self.screen_observer.capture_as_pil(region=region)
            else:
                img = self.screen_observer.capture_as_pil()
                self.screen_size = img.size
            
        img.thumbnail((1024, 1024))
        output = BytesIO()
        img.save(output, format="JPEG", quality=60)
        return output.getvalue()

    def set_roi(self, center_x: int, center_y: int, zoom_factor: float = 2.0):
        self.current_roi = ROIManager.calculate_roi(center_x, center_y, zoom_factor, self.screen_size)
        logger.info(f"[LiveStreamer] ROI set to {self.current_roi}")

    def reset_roi(self):
        self.current_roi = None
        logger.info("[LiveStreamer] ROI reset.")

    async def stream_screen_loop(self, fps: float = 1.0):
        logger.info(f"[LiveStreamer] Starting screen stream at {fps} fps")
        interval = 1.0 / fps
        while self.is_streaming and self.session:
            try:
                frame_bytes = self._capture_screen_compressed()
                await self.session.send(
                    input=types.LiveClientRealtimeInput(
                        media_chunks=[types.Blob(mime_type="image/jpeg", data=frame_bytes)]
                    )
                )
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"[LiveStreamer] Stream loop error: {e}")
                break

    async def send_frame_now(self):
         if not self.session or not self.is_streaming: return
         try:
              frame_bytes = self._capture_screen_compressed()
              await self.session.send(
                  input=types.LiveClientRealtimeInput(
                      media_chunks=[types.Blob(mime_type="image/jpeg", data=frame_bytes)]
                  )
              )
         except Exception as e:
              logger.error(f"[LiveStreamer] Print frame error: {e}")

    async def send_prompt(self, text: str):
         if not self.session or not self.is_streaming: return
         await self.session.send(
             input=types.LiveClientContent(
                 turns=[types.Content(role="user", parts=[types.Part.from_text(text=text)])],
                 turn_complete=True
             )
         )

    async def _listen_for_responses(self):
        try:
            async for response in self.session.receive():
                if response.server_content:
                    if response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            if part.text:
                                try:
                                    json_data = json.loads(part.text)
                                    if self.on_response_callback: self.on_response_callback(json_data)
                                except json.JSONDecodeError:
                                    if self.on_response_callback: self.on_response_callback({"text_response": part.text})
                            if part.inline_data:
                                self.audio_out_queue.put(part.inline_data.data)
        except asyncio.CancelledError: pass
        except Exception as e:
             logger.error(f"[LiveStreamer] Listener error: {e}")
             self.is_streaming = False

    def _setup_audio_streams(self):
        def input_callback(indata, frames, time, status):
            self.audio_in_queue.put(indata.copy())
        def output_callback(outdata, frames, time, status):
             try:
                 data = self.audio_out_queue.get_nowait()
                 decoded = np.frombuffer(data, dtype='int16')
                 chunk_len = min(len(decoded), frames)
                 outdata[:chunk_len] = decoded[:chunk_len].reshape(-1, 1)
                 if chunk_len < frames: outdata[chunk_len:] = 0
             except queue.Empty: outdata.fill(0)

        self._audio_input_stream = sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16', callback=input_callback)
        self._audio_output_stream = sd.OutputStream(samplerate=24000, channels=1, dtype='int16', callback=output_callback)
        self._audio_input_stream.start()
        self._audio_output_stream.start()

    async def _stream_audio_input_loop(self):
        while self.is_streaming and self.session:
            try:
                data = await asyncio.to_thread(self.audio_in_queue.get, timeout=1.0)
                await self.session.send_realtime_input(audio={"data": data.tobytes(), "mime_type": "audio/pcm"})
            except queue.Empty: continue
            except Exception: break

    def _cleanup_audio(self):
        if self._audio_input_stream: self._audio_input_stream.stop(); self._audio_input_stream.close()
        if self._audio_output_stream: self._audio_output_stream.stop(); self._audio_output_stream.close()

    def set_callback(self, callback: Callable[[Dict[str, Any]], None]):
        self.on_response_callback = callback

    def send_step_feedback(self, text: str, loop: Optional[asyncio.AbstractEventLoop] = None):
        """Sends feedback about a step outcome to provide context for the next frame."""
        if not self.session or not self.is_streaming: return
        target_loop = loop or asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(self.send_prompt(f"STEP_FEEDBACK: {text}"), target_loop)
