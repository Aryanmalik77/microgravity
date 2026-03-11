# Semantic UI Context & Pointer Verification (Phase 6)

## Overview
Phase 6 introduced deep semantic understanding of app topology and physical verification of mouse movements.

## Semantic UI Topology
- **App Characterizer**: Guesses the utility of large regions (Sidebars, Menus, Chat Feeds) rather than just identifying atomic elements.
- **Contextual Labeling**: Surfaces labels like "Primary Navigation" or "Thread Header" in the world model to improve reasoning quality.

## Pointer Verification
- **Mechanism**: After calculating coordinates but before clicking, the agent moves the physical mouse pointer to the target.
- **Verification**: A micro-crop around the pointer is taken. The agent verifies: "Is the mouse cursor physically resting on the intended element?"
- **Benefit**: Prevents misclicks caused by coordinate drift or overlap.

## Consequence Analysis
- **Intent vs Outcome**: After every action, the system evaluates: "Did the screen change as expected for this intent?"
- **Error Types**: Explicitly classifies errors like `WRONG_INSTANCE` (clicking the background instead of a modal) to trigger autonomous resolution strategies.
