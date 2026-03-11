# Edge Detection & Positional Correlation System

## Problem

The CV pipeline detects UI elements via contour analysis and classifies them by aspect ratio, but:
1. **No structural fingerprinting** — two buttons at different positions look identical to the system
2. **No relational context** — the pipeline doesn't know "this button is next to that input field"
3. **No persistent IDs** — elements lose identity across frames/sessions
4. **No edge topology** — Canny/Sobel edge maps aren't used for structural signatures
5. **Complex UIs** (e.g., Chrome settings, VSCode panels) overwhelm flat element lists

## Solution: Edge-Correlated Structural IDs

A new `EdgeCorrelator` module that:
1. Extracts **Canny edge maps** → structural boundary signatures
2. Computes **positional correlation** between detected edges → relational graph
3. Assigns **Correlational IDs** (deterministic hashes of edge topology + position + neighbors)
4. Pre-indexes elements **before/after** static VLM calls to reduce token cost
5. Exposes as **agentic tools** for learning new apps and processing complex UIs

### Architecture

```
Screen Frame
     │
     ├─→ [Canny Edge Map] → edge density, gradient orientation
     │
     ├─→ [Contour Detection] → bounding boxes (existing)
     │
     └─→ [EdgeCorrelator]
            │
            ├─ Edge Signature: hash(dominant_angles + edge_density + corner_count)
            ├─ Positional Graph: {elem_A → [left_of: elem_B, above: elem_C]}
            ├─ Correlational ID: sha256(edge_sig + relative_neighbors + element_type)
            │
            └─ VLM Index: pre/post maps for efficient Static VLM queries
```

---

## Proposed Changes

### New Module

#### [NEW] [edge_correlator.py](file:///c:/Users/HP/Downloads/micro%20gravity%20-%20Copy/ui_agent_engine/src/perception/edge_correlator.py)

**Class `EdgeCorrelator`:**

| Method | Purpose |
|---|---|
| `compute_edge_map(frame)` | Canny + Sobel gradient → edge density map, gradient orientations |
| `extract_edge_signature(crop)` | Per-element: dominant angles, edge density, corner count → compact vector |
| `build_positional_graph(elements)` | Spatial proximity graph: left_of, right_of, above, below, inside, adjacent |
| `assign_correlational_ids(elements, graph)` | Deterministic hash = edge_sig + relative_position + neighbors → `CID_xxxx` |
| `pre_index_for_vlm(elements, cids)` | Generates annotated element map for VLM with CIDs |
| `post_index_from_vlm(vlm_response, cids)` | Maps VLM labels back to elements via CIDs |
| `find_element_by_cid(cid)` | Recall element by correlational ID |
| `diff_structural_layout(cids_before, cids_after)` | Detects layout changes between frames |

**Data structures:**
```python
@dataclass
class EdgeSignature:
    dominant_angles: List[float]   # Top 4 gradient orientations (0-180°)
    edge_density: float            # % of pixels that are edges
    corner_count: int              # Harris/Shi-Tomasi corner count
    line_segments: int             # Hough line count
    signature_hash: str            # compact hash for fast comparison

@dataclass
class CorrelatedElement:
    element: UIElement
    cid: str                       # Correlational ID (CID_xxxx)
    edge_sig: EdgeSignature
    neighbors: Dict[str, str]      # {relation: neighbor_cid}
    structural_context: str        # "button left_of text_input, below toolbar"
```

**Correlational ID formula:**
```
CID = sha256(
    edge_density_quantized +
    dominant_angle_bucket +
    element_type +
    neighbor_types_sorted +
    relative_position_in_parent +
    corner_count_bucket
)[:12]
```

This produces a **stable, position-aware ID** that persists across frames as long as the structural neighborhood doesn't change.

---

### Modifications

#### [MODIFY] [cv_pipeline.py](file:///c:/Users/HP/Downloads/micro%20gravity%20-%20Copy/ui_agent_engine/src/perception/cv_pipeline.py)

- Add `compute_canny_edges()` method → returns edge map + gradient magnitudes
- Integrate `EdgeCorrelator` into `full_analysis()` → auto-assigns CIDs
- Add `UIElement.cid` field to the dataclass
- Add `get_structural_map()` method → returns annotated element graph

#### [MODIFY] [cv_logger.py](file:///c:/Users/HP/Downloads/micro%20gravity%20-%20Copy/ui_agent_engine/src/perception/cv_logger.py)

- Add `log_edge_detection()` method → logs edge density, corner count, CID assignments
- Add `log_structural_diff()` method → logs layout changes between frames

#### [MODIFY] [agentic_planner.py](file:///c:/Users/HP/Downloads/micro%20gravity%20-%20Copy/ui_agent_engine/src/planning/agentic_planner.py)

- Add 3 new CV tool actions:
  - `cv_edge_detect` — run edge detection + assign CIDs to all visible elements
  - `cv_structural_map` — get the full positional graph with CIDs
  - `cv_find_by_cid` — locate a specific element by its correlational ID

#### [MODIFY] [ui_agent.py](file:///c:/Users/HP/Downloads/micro%20gravity%20-%20Copy/ui_agent_engine/src/agent_core/ui_agent.py)

- Add 3 new CV tool dispatchers for edge detection tools
- Integrate CID-annotated screenshots into the observation cycle

---

## Advanced Use Cases

### 1. Learning New Applications
When the agent encounters an unseen app, it runs edge detection + CID assignment on the full window. This produces a **structural blueprint** that maps:
- Toolbar (CID_a1b2) → contains [button CID_c3d4, button CID_e5f6, dropdown CID_g7h8]
- Sidebar (CID_i9j0) → contains [tree_item CID_k1l2 ...]

This blueprint persists in hierarchical memory under `app_instances/{app_name}/structural_blueprint`.

### 2. Complex UI Simplification
For dense UIs (VSCode, Chrome DevTools), the edge correlator groups elements into **structural clusters** based on proximity and edge continuity. Instead of sending 200+ flat elements to VLM, it sends ~15-20 clusters with CIDs, dramatically reducing token cost.

### 3. Cross-Frame Element Tracking
CIDs are stable across frames if the structural neighborhood is unchanged. This enables:
- **Element re-identification after scroll** — same CID means same element
- **State change detection** — same CID but different fingerprint = state changed
- **Animation tracking** — CID disappears then reappears = transient animation

### 4. VLM Pre/Post Indexing
**Before VLM call:** Send annotated screenshot with CID labels overlaid → VLM references elements by CID.
**After VLM call:** Map VLM response CIDs back to exact pixel coordinates → instant action resolution without re-detection.

---

## Verification Plan

### Automated Tests (add to `test_cv_efficacy.py`)
- Test 11: Edge signature stability — same element → same edge_sig across frames
- Test 12: CID determinism — same layout → same CIDs
- Test 13: Positional graph correctness — verify left_of/above relationships
- Test 14: Structural diff — detect added/removed elements between frames
- Test 15: VLM index roundtrip — pre-index → mock VLM → post-index maps correctly
