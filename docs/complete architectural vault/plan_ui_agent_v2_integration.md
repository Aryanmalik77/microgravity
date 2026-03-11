# 🤖 UI Agent V2 Integration & Kernel Architecture

## Overview
The UI Agent V2 introduces a more robust, state-aware execution environment centered around the `KernelLoop`. This architecture shifts from linear script execution to a continuous Observe-Think-Act loop with integrated safety and introspection.

## Core Components

### 🔄 KernelLoop (`src/kernel/loop.py`)
The central nervous system of the agent. It manages:
- **State Persistence**: Ensuring the agent knows its current position and objective.
- **Cognitive Mode Switching**: Dynamically switching between `DETERMINISTIC` (rule-based) and `NON_DETERMINISTIC` (LLM-driven) execution.
- **Error Remediation**: Automatically attempting to fix failures before reporting to the user.

### 🛡️ Introspection Engine (`src/kernel/introspection.py`)
A multidimensional verification layer that audits agent actions:
- **Pass 1: Syntax & Schema**: Basic validation of tool calls.
- **Pass 2: Safety & Policy**: Ensures actions follow security and safety guidelines.
- **Pass 3: Intent Alignment**: Compares the *perceived outcome* vs. the *user's original intent*.

### 🧠 Diffused Attention Monitor (`src/intelligence/cognition.py`)
A background cognitive task that:
- Periodically scans the screen for unexpected UI changes (popups, errors).
- Alerts the main loop if an anomaly is detected, even if it's not related to the current objective.

### 📼 Episodic Memory (`src/memory/kernel.py`)
Transitioned to **LMDB (HISTORY_v2)** for high-performance structured storage:
- **JSON-based episodes**: Storing full state transitions including screenshots and tool outputs.
- **Semantic Tagging**: Enabling fast retrieval of past experiences (e.g., `#failed_login`, `#successful_search`).

## Execution Flow
1. **Initialize**: Load objective and environment state.
2. **Observe**: Capture screen and current UI state via `VisionEngine`.
3. **Think**: `ActionPredictor` determines the next best step.
4. **Act**: Execute tool (Mouse/Keyboard/Browser).
5. **Introspect**: Verify outcome. If alignment is > 90%, proceed. Otherwise, remediate.
6. **Learn**: Log episode to LMDB and update `TaskClassifier` heuristics.

## Future Roadmap
- [ ] Multi-Modal Feedback: Integrating audio/voice status updates.
- [ ] Collaborative Loops: Allowing multiple agents to share a single `KernelLoop` context.
