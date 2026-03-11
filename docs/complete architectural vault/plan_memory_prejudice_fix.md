# Element Disambiguation & Memory Prejudice Fix (Phase 10)

## The "Memory Prejudice" Problem
- **Issue**: The agent developed a "prejudice" for specific global coordinates. For example, clicking an old "Log In" button on the top bar instead of the new "Log In" button inside an active dialog.
- **Root Cause**: Element labels were stored without sufficient spatial context or "active container" awareness.

## Multi-tier Fixes

### 1. Element Disambiguation Logic
- The `AgenticPlanner` now identifies elements with identical labels using spatial context (e.g., "Log In button inside the modal" vs. "Log In button on the page").
- **Constraint**: If a modal/dialog is detected, interaction is strictly restricted to elements *within* that modal's boundaries.

### 2. Coordinate-Aware Failure Analysis
- `LearningLoop` now includes a `WRONG_INSTANCE` failure class.
- It detects when the agent clicks the same label at the same (wrong) coordinates repeatedly.

### 3. Coordinate-Based Anti-Prejudice Blacklist
- The system now tracks **(Target Label, Target Coordinates)** pairs in the failure history.
- When an action fails, the exact pixels are blacklisted for the current task iteration.
- If the agent tries to click the same label again, the Planner is explicitly told: **"Clicking [Label] at [X, Y] failed. SEARCH for the element at a different spatial location."**

### 4. Pointer Verification Recovery
- Triggers an automatic high-precision zoom and physical pointer movement to verify the element is truly the intended target before the click is committed.
