# UI Agent 5-Layer Awareness Stack (Phases 1-3)

## Architectural Vision
Modernizes the UI Agent from a "shallow" visual actor to a structural observer with multi-dimensional awareness.

## The 5-Layer Stack

### Layer 1: OS & Window Awareness (`os_awareness.py`)
- **Window State Ledger**: Tracks HWND, Title, Class, Z-order, and exact pixel boundaries (Client vs Outer rect).
- **Process Mapping**: Links windows to system PIDs and resource usage (CPU/RAM).
- **Snap/Anchor Detection**: Identifies if windows are snapped to quadrants or anchored in specific layouts.

### Layer 2: Application Awareness (`app_characterizer.py`)
- **Topology Mapping**: Identifies high-level structures like Sidebars, Toolbars, Tab Bars, and Menu strips.
- **Interaction Models**: Learns what an app *can* do (Scroll, Click, Drag, Type) based on its profile.
- **Tab Criticality**: High-awareness mode for browsers and editors where tab state is paramount.

### Layer 3: Element Awareness (`element_boundary_learner.py`)
- **Precision Boundaries**: Learns exact pixel targets for Close/Min/Max buttons, icons, and menus.
- **Hybrid Probing**: Combines Win32 API probing + CV contour analysis + VLM labeling.

### Layer 4: Situational Awareness (`situational_awareness.py`)
- **World Model**: Merges L1-L3 into a coherent global state.
- **Overlap Resolution**: Detects if targets are occluded by other windows and generates "Smart Focus" strategies.

### Layer 5: Experiential Memory (`experiential_memory.py`)
- **Episodic**: "What happened."
- **Hypothesis**: "Why it happened."
- **Process**: Reusable action sequences.
- **Nuance**: Known quirks and edge cases of specific apps.
