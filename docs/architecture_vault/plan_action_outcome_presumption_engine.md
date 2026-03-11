# Plan: Action Outcome Tracking & Presumption Engine (Phases 12 & 13)

## Objective
Implement advanced computer vision (CV) and experiential learning capabilities centered around structural element identification and high-speed action resolution.

## Components

### 1. Edge Detection & Correlational ID (Phase 12)
- **Module**: `edge_correlator.py`
- **Features**: Canny edge detection, Sobel gradients, and structural hashing.
- **Goal**: Assign deterministic, stable IDs (CIDs) to UI elements to track them across slightly different visual states without falling back to full VLM analysis.

### 2. Action Outcome Tracking (Phase 13)
- **Module**: `action_outcome_tracker.py`
- **Features**: 3-tier outcome system (SUCCESS, SEMI_SUCCESS, FAILED) with failure categories (e.g., NO_EFFECT, UNINTENDED_ACTION).
- **Goal**: Build a statistical profile of action reliability for every element and application context.

### 3. Presumption Engine (Phase 13)
- **Module**: `presumption_engine.py`
- **Features**: Hierarchical cache (site -> app -> global) of high-confidence element locations.
- **Goal**: Enable "Tier 0" resolution—executing actions based on pre-learned beliefs without invoking the VLM or template matching, significantly reducing latency for common tasks.

### 4. Postponed Judgement (Phase 13)
- **Module**: `postponed_judgement.py`
- **Features**: Deferral of outcome evaluation for multi-step sequences (e.g., scrolling).
- **Goal**: Evaluate the "group success" of a sequence rather than failing at an intermediate step that provides no immediate visual feedback.

## Integration
- **DecisionManager**: Adds Tier 0 (Presumption Engine) to the resolution pipeline.
- **LearningLoop**: Uses the Outcome Tracker to classify results and the Presumption Engine to store winning locations.
- **AgenticPlanner**: Contextually aware of successful "fast-action" candidates to prefer learned paths.

## Verification
- Comprehensive 18-test suite in `test_cv_efficacy.py` covering all new logic paths.
- 100% Pass Rate achieved on Windows environment.
