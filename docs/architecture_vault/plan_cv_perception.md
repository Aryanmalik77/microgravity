# CV Perception Pipeline & Decision Manager (Phase 4)

## Central OpenCV Pipeline (`cv_pipeline.py`)
Standardizes 6 high-speed CV modes to reduce VLM dependency:
- **Multi-Scale Template Match**: Handles DPI/Zoom variations (0.8x - 1.2x).
- **Feature Matching (ORB)**: Matches elements that change style or rotate.
- **Text Region Detection**: MSER-based localization of text WITHOUT OCR.
- **Stability Analysis**: Frame differencing to isolate STATIC vs DYNAMIC regions.
- **Color Fingerprinting**: Histogram signatures for state detection (Hover/Active).

## Speculative Snipping
- **Mechanism**: The agent proactively crops and saves `speculative_snips` of elements it expects to interact with.
- **Validation**: Subsequent actions use these snips for fast template verification rather than raw screen analysis.

## Decision Manager Architecture
A multi-tier routing engine that chooses the most efficient resolution path:
1. **Tier 1 (Cache)**: RAM hit → Immediate action (<5ms).
2. **Tier 2 (CV Match)**: Multi-scale/ORB match in STATIC regions (<50ms).
3. **Tier 3 (Live API)**: Precision zoom / Live bounding box (0.5s - 2s).
4. **Tier 4 (Static VLM)**: Full screenshot analysis fallback (5s+).

## LLM Skip Optimization
- If an action is a repeat of a proven successful path AND the target region is STATIC, the system skips the Agentic Planner (LLM) entirely and replays the cached action.
