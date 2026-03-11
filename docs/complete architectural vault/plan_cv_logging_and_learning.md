# Advanced CV Testing, Logging, Experiential Learning & Function Calling

## Goal
Enhance the UI Agent with:
1. **Structured CV Logging** — Every template match, snip, ORB match, and embedding comparison emits structured logs with timestamps, confidence scores, and visual artifacts.
2. **Active vs Passive Matching** — Differentiate between proactive element scans (passive/background) and targeted action resolution (active/foreground).
3. **Hierarchical Experiential Learning Library** — Upgrade the flat 4-tier memory into a tree-structured knowledge base with cross-app generalization.
4. **Function-Calling Orchestration** — Let the agent explicitly invoke CV tools (template match, zoom, snip, fingerprint) via structured function calls in the planning prompt.

---

## User Review Required

> [!IMPORTANT]
> This plan adds a new `cv_logger.py` module and significantly modifies `experiential_memory.py`. The hierarchical memory will auto-migrate existing flat data on first load.

> [!WARNING]
> The function-calling schema change in `agentic_planner.py` means the Gemini prompt grows by ~400 tokens. This is offset by the LLM-skip optimization for cached actions.

---

## Proposed Changes

### Component 1: CV Structured Logging

#### [NEW] cv_logger.py
**Path**: `ui_agent_engine/src/perception/cv_logger.py`

A centralized logger that every CV module calls. Emits structured JSON log lines to both console and a rotating log file.

```python
class CVLogger:
    """Structured logging for all CV operations."""
    
    def __init__(self, log_dir="cv_logs", console=True, file=True):
        self.log_dir = log_dir
        self.console = console
        self.file = file
        self._session_id = generate_session_id()
    
    def log_template_match(self, target, scale, confidence, coords, matched, latency_ms):
        """Logs a template match attempt with full metadata."""
        # Output: [CV:TEMPLATE] target="search_bar" scale=1.0 conf=0.92 
        #         coords=(120,50) matched=True latency=4.2ms
    
    def log_orb_match(self, target, num_keypoints, num_matches, confidence, matched):
        """Logs an ORB feature matching attempt."""
    
    def log_snip_save(self, element_id, bbox, source, is_speculative):
        """Logs when a UI element crop is saved (speculative or confirmed)."""
    
    def log_embedding_compare(self, query_id, top_match_id, top_score, candidates_count):
        """Logs an embedding similarity search."""
    
    def log_stability_scan(self, num_static, num_dynamic, num_transient, scan_time_ms):
        """Logs a stability classification pass."""
    
    def log_text_region(self, num_regions, total_area_pct):
        """Logs text region detection results."""
    
    def log_fingerprint(self, element_id, fingerprint_hash, state_change_detected):
        """Logs a color fingerprint computation/comparison."""
    
    def log_active_match(self, target, method, result, context="action_resolution"):
        """Logs an ACTIVE match (triggered by agent decision)."""
    
    def log_passive_match(self, target, method, result, context="background_scan"):
        """Logs a PASSIVE match (triggered by observation cycle)."""
    
    def get_session_summary(self) -> dict:
        """Returns aggregated stats for the current session."""
```

**Log Format** (JSON Lines):
```json
{"ts": 1709654400.123, "session": "s_abc123", "op": "TEMPLATE_MATCH", "mode": "ACTIVE",
 "target": "Log In", "scale": 1.0, "confidence": 0.92, "coords": [120, 50],
 "matched": true, "latency_ms": 4.2}
```

---

#### [MODIFY] cv_pipeline.py
Inject `CVLogger` calls into every public method:

- `match_template_multiscale()` → `log_template_match()` after each scale attempt + final result
- `match_features_orb()` → `log_orb_match()` with keypoint and match counts
- `detect_ui_elements()` → Summary log: element count, types detected, NMS eliminations
- `detect_text_regions()` → `log_text_region()` with region count
- `classify_regions()` → `log_stability_scan()` with STATIC/DYNAMIC/TRANSIENT counts
- `fingerprint_element()` → `log_fingerprint()` with hash
- `build_element_embedding()` → `log_embedding_compare()` when used in similarity search
- `full_analysis()` → Summary log with total time and per-module breakdown

---

#### [MODIFY] decision_manager.py
Log which tier resolved the action and why higher tiers were skipped:
```
[DM:RESOLVE] target="Log In" tier=3(CV_CACHE) conf=0.91 latency=2ms 
             skipped=[PROCESS_REPLAY(no_match), BOUNDARY(not_learned)]
```

---

#### [MODIFY] action_predictor.py
Log the full resolution pipeline for each action:
```
[PREDICTOR] target="search_bar" attempted=[CV_VERIFY:0.88, ZOOM_RESOLVE:0.95] 
            final_coords=(320,55) method=ZOOM latency=1200ms
```

---

### Component 2: Active vs Passive Matching

#### [MODIFY] cv_pipeline.py
Add a `mode` parameter to key methods:

```python
def match_template_multiscale(self, screen, template, threshold=0.80, 
                               mode="PASSIVE"):  # NEW param
    """mode: ACTIVE (agent-triggered) or PASSIVE (background scan)"""
```

- **PASSIVE Mode** (called during `full_analysis()` observation cycle):
  - Lower priority, can be throttled
  - Results cached for future ACTIVE lookups
  - Logged as background discovery
  
- **ACTIVE Mode** (called during `resolve_action()` or `predict_action_parameters()`):
  - High priority, no throttling
  - Triggers zoom fallback if confidence < threshold
  - Logged as targeted resolution

#### [MODIFY] decision_manager.py
Tag each resolution attempt with its mode:
- Tiers 1-3 (cache/boundary/atlas) → PASSIVE pre-computed results used actively
- Tiers 4-6 (CV match/Live API/VLM) → ACTIVE on-demand resolution

---

### Component 3: Hierarchical Experiential Learning Library

#### [MODIFY] experiential_memory.py
Restructure from flat lists to a **hierarchical tree**:

```
ExperientialMemory/
├── global/               # Cross-app knowledge
│   ├── hypotheses/       # "All browsers have address bars at top"
│   ├── processes/        # "Login flow: find username → type → find password → type → click submit"
│   └── nuances/          # "Modal dialogs block background clicks"
├── app_classes/
│   ├── BROWSER/
│   │   ├── episodes/
│   │   ├── hypotheses/
│   │   ├── processes/
│   │   └── nuances/
│   ├── EDITOR/
│   │   └── ...
│   └── CHAT/
│       └── ...
└── app_instances/
    ├── Chrome/
    │   ├── episodes/
    │   ├── site_specific/   # NEW: per-website knowledge
    │   │   ├── reddit.com/
    │   │   └── google.com/
    │   └── ...
    └── VSCode/
        └── ...
```

**New Methods**:

```python
# --- Hierarchical Recall ---
def recall_hierarchical(self, task, app_class, app_instance="", site=""):
    """Searches from most specific to most general:
    1. site_specific → 2. app_instance → 3. app_class → 4. global
    Merges results with specificity weighting."""

# --- Cross-App Generalization ---
def promote_to_global(self, hypothesis_id):
    """Promotes an app-specific hypothesis to global if confirmed across 3+ apps."""

def extract_cross_app_patterns(self):
    """Scans all app_class knowledge for common patterns and auto-promotes."""

# --- Hierarchical Process Library ---
def find_process_hierarchical(self, task, app_class, app_instance=""):
    """Searches: instance → class → global. Returns best match with source level."""

# --- Learning Metrics ---
def get_learning_stats(self) -> dict:
    """Returns: total episodes, hypotheses (by confidence tier), processes (by category),
    nuances (by severity), cross-app promotions, recall hit rates."""
```

**Migration**: On first load, existing flat data is auto-sorted into the hierarchy by `app_class` field.

---

### Component 4: Function-Calling Orchestration

#### [MODIFY] agentic_planner.py
Add explicit CV tool definitions to the system prompt so the LLM can invoke them:

```python
AVAILABLE_CV_TOOLS = """
You have access to these CV analysis tools. Use them when needed:

1. cv_template_match(target_label, threshold=0.80)
   → Searches for a known element template on screen.
   → Returns: {matched, coords, confidence} or null.
   → USE WHEN: You need to find a previously seen element.

2. cv_snip_element(element_label, bbox=[x,y,w,h])
   → Crops and saves the element at the given bounding box for future matching.
   → Returns: {saved, template_path}
   → USE WHEN: You discover a new important element.

3. cv_fingerprint_compare(element_label)
   → Compares current element appearance to stored fingerprint.
   → Returns: {same_state, similarity, state_change_detected}
   → USE WHEN: You need to check if a button changed state (hover, active, disabled).

4. cv_stability_check(region=[x,y,w,h])
   → Checks if a screen region is STATIC or DYNAMIC.
   → Returns: {classification, confidence}
   → USE WHEN: You want to know if an area is safe to cache.

5. cv_embedding_search(target_description)
   → Finds elements visually similar to the description.
   → Returns: [{element_id, similarity_score, coords}]
   → USE WHEN: You can't find an exact template but know what the element looks like.

6. request_closeup_zoom(target_label, hint_coords=[x,y])
   → Triggers the 2-pass precision zoom on a small target.
   → Returns: {coords, confidence, verified}
   → USE WHEN: Target is tiny or overlapping with other elements.
```

The planner should output structured tool calls like:
```json
{"intent": "cv_template_match", "params": {"target_label": "Log In", "threshold": 0.85}}
```

#### [MODIFY] ui_agent.py
Add a tool dispatcher in `_execute_action()` that intercepts CV tool intents:

```python
CV_TOOL_HANDLERS = {
    "cv_template_match": self._handle_cv_template_match,
    "cv_snip_element": self._handle_cv_snip_element,
    "cv_fingerprint_compare": self._handle_cv_fingerprint_compare,
    "cv_stability_check": self._handle_cv_stability_check,
    "cv_embedding_search": self._handle_cv_embedding_search,
    "request_closeup_zoom": self._handle_closeup_zoom,
}
```

Each handler:
1. Captures current screen
2. Invokes the corresponding `CVPipeline` method
3. Logs via `CVLogger`
4. Returns structured result to the planner for next-step reasoning

---

### Component 5: Advanced Testing Efficacy

#### [NEW] test_cv_efficacy.py
**Path**: `ui_agent_engine/tests/test_cv_efficacy.py`

Comprehensive test suite that measures real-world matching accuracy:

```python
class TestCVEfficacy:
    """Measures template matching accuracy, speed, and reliability."""
    
    def test_multiscale_accuracy(self):
        """Tests match at 0.8x, 1.0x, 1.2x scales with known ground truth."""
    
    def test_orb_rotation_tolerance(self):
        """Tests ORB matching with 15°, 30°, 45° rotated templates."""
    
    def test_fingerprint_state_detection(self):
        """Tests fingerprint change detection for hover/active/disabled states."""
    
    def test_embedding_cross_app_similarity(self):
        """Tests if 'close button' embeddings match across Chrome, VSCode, Notepad."""
    
    def test_stability_classifier_accuracy(self):
        """Feeds known static+dynamic frames, measures classification accuracy."""
    
    def test_nms_deduplication(self):
        """Verifies NMS correctly eliminates overlapping detections."""
    
    def test_active_vs_passive_latency(self):
        """Measures latency difference between active and passive modes."""
    
    def test_decision_manager_tier_routing(self):
        """Verifies the correct tier is chosen for different scenarios."""
    
    def test_hierarchical_memory_recall(self):
        """Verifies hierarchical recall searches specific→general correctly."""
    
    def test_cross_app_generalization(self):
        """Tests that hypotheses confirmed in 3+ apps get promoted to global."""
```

---

## Verification Plan

### Automated Tests
```bash
cd "c:\Users\HP\Downloads\micro gravity - Copy\ui_agent_engine"
python -m pytest tests/test_cv_efficacy.py -v
```

### Live Agent Verification
Run `test_reddit_agentic.py` and verify:
1. **Console shows structured CV logs** for every match attempt
2. **Active matches** are tagged `[CV:ACTIVE]` during click resolution
3. **Passive matches** are tagged `[CV:PASSIVE]` during observation
4. **Hierarchical memory** correctly stores Reddit-specific knowledge under `app_instances/Chrome/site_specific/reddit.com/`
5. **Function calls** appear in the planner output (e.g., `cv_template_match("Log In")`)

### Log File Verification
Check `cv_logs/session_*.jsonl` for structured entries with complete metadata.
