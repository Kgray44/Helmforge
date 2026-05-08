# Post-RC 4A Tuning Pages Usability Report

Post-RC 4A improves the Base Tuning, Filtering, and Combat Profile pages after the Phase 19D release-candidate freeze. The pass is UI/usability only: telemetry and existing runtime truth remain the truth surface, simulation mode remains available, and no hardware polling, vJoy writes, output verification, Bridge lifecycle management, recorder backend, game injection, cloud AI/LLM behavior, or auto-save behavior was added.

## pages changed

- `v3_app/pages/base_tuning_page.py`
- `v3_app/pages/filtering_page.py`
- `v3_app/pages/combat_profile_page.py`
- Shared support in `v3_app/pages/page_helpers.py`, `v3_app/pages/graph_widgets.py`, `v3_app/pages/graph_data.py`, `v3_app/ui/shell.py`, `v3_app/theme/qss.py`, and the existing Post-RC 1B metadata registry.

## axis selection fixes

The Mapped Axes blocks now use selectable axis buttons for Roll, Pitch, Throttle, Yaw, Aux 1, and Aux 2. Selecting an axis updates the page session state, visually highlights the selected axis, refreshes the parameter fields, updates the response preview, refreshes Live Snapshot values, and updates the Guidance note for that selected axis.

The shell now passes the existing workspace draft callback to the three tuning pages so committed tuning edits update the in-memory draft the same way the Mapping page does.

## validators and dropdowns

Base Tuning Curve Mode now uses a non-editable dropdown. The dropdown is limited to the currently supported `s` mode because the shared pipeline does not yet implement additional curve families.

Numeric fields on Base Tuning, Filtering, and Combat Profile use the existing Post-RC 1B metadata min/max values. On commit, invalid text is rejected, out-of-range values are clamped, and the workspace draft is updated only with valid numeric values.

## live snapshot readability

The Live Snapshot blocks now use scan-friendly rows:

- Input Source
- Selected Axis
- Raw Value
- Output Intent
- Runtime Truth
- Output Verification

The main value is larger and reflects the current output intent for the selected page preview. Output verification remains explicit and false unless the runtime truth object says otherwise.

## guidance readability

Guidance blocks now use compact sections instead of one sparse sentence:

- Current feel
- What this setting affects
- Suggested range
- Caution
- Selected axis note

The copy stays page-specific and selected-axis-aware without expanding into the later Help / Docs overhaul.

## graph live dots

`GraphPreview` now supports named reusable marker items. Base Tuning adds live dots for Linear and Adjusted. Filtering adds current sample dots for Input, Filtered, and Sample. Combat Profile adds live dots for Linear, Baseline, and Combat.

Graph series items and marker items are reused between updates; marker movement updates data in place instead of clearing and rebuilding the graph widget on each heartbeat.

## remaining page-specific polish

- Broader curve-mode families should stay hidden until the shared pipeline actually supports them.
- Filtering preview could later get richer time-history context if a future pass expands the graph model.
- Full Help / Docs integration for these field-level behaviors remains deferred.
- Mapping HOTAS diagram, real Flight Recorder backend, and runtime authority changes remain outside this pass.

## runtime truth preservation

Post-RC 4A does not change Full Live Runtime Ready logic. vJoy detected is still not output verification. Physical input alone is still not Full Live Runtime Ready. Output intent is still not output write proof. Fake/test paths and packaged smoke remain separate from real runtime readiness. Simulation mode remains available.
