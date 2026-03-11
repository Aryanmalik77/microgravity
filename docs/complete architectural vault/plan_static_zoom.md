# Static vs Dynamic Analysis & Precision Targeting (Phase 5)

## Overview
This phase focused on temporal stability analysis and autonomous precision targeting for tiny UI elements.

## Temporal Stability (Static/Dynamic Classifier)
- **Mechanism**: Captures a temporal buffer of frames (approx. 0.5s) to classify regions as STATIC, DYNAMIC, or TRANSIENT.
- **Benefit**: Allows the agent to skip redundant screenshots in stable regions, drastically reducing latency for invariant elements.

## Precision Zoom Strategy
- **Autonomous Trigger**: The agent detects when a target is physically small (e.g. <400px area) or when confidence is low.
- **Two-Pass Execution**:
    1. **Overview Pass**: Locate the general area of the element.
    2. **Closeup Pass**: Real-time ROI zoom (3x magnification) to resolve exact pixel centers.
- **Integration**: Integrated into `action_predictor.py` and `ui_agent.py` as `resolve_target_with_zoom`.

## Contextual Awareness
- **Bounding Boxes**: Explicit pixel coordinate bounding boxes are injected into the planner context for every detected element.
- **Failure Introspection**: History of failed clicks is surfaced to avoid "memory prejudice" and repetition loops.
