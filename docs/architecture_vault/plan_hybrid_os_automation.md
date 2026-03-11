# 🌐 Hybrid OS & Browser Automation Architecture

## Overview
This architecture enables seamless automation across the OS boundary, combining the strengths of Native UI control (Image-based) and Browser-level control (DOM-based).

## Integrated Technologies

### 🤏 PinchTab
- **Role**: State Capture & Extraction.
- **Mechanism**: Connects via Chrome DevTools Protocol (CDP).
- **Strength**: Provides token-efficient snapshots of the DOM for high-speed analysis of page content.

### 🤖 UI Agent Engine
- **Role**: Native Interaction.
- **Tools**: `MouseController`, `KeyboardController`.
- **Strength**: Can interact with anything on the screen (Flash, Canvas, App Windows) without needing a DOM.

### 🎣 Stagehand Integration
- **Role**: High-level Browser Orchestration.
- **Mechanism**: Uses Playwright-driven AI actions on the same CDP session.

## Collaborative Workflow
1. **Navigate**: Use `PinchTab` or `Stagehand` to open URLs and handle basic navigation.
2. **Interact**: When encountering non-standard UI or security blockers (like Google Sign-in buttons), the system switches to the **UI Agent** for native mouse/keyboard execution.
3. **Verify**: Use visual screenshots from `ScreenObserver` to confirm the state matches the `PinchTab` snapshot.

## Key Scripts
- `scripts/telegram_hybrid.py`: Hybrid Telegram automation.
- `scripts/reddit_ui_agent_integration.py`: Combined login and data extraction.
- `scripts/run_github_task.py`: Multi-step automation through Google Auth.

## Advantages
- **Bypass Detection**: Native mouse movements are less detectable than `element.click()`.
- **Versatility**: Works for both web apps and desktop applications.
- **Resilience**: If the DOM changes, visual localization provides a robust fallback.
