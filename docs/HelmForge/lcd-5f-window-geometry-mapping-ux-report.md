# LCD-5F Window Geometry, Mapping UX, and Advanced Route Cleanup

## Off-screen window symptom

LCD-5 left initial window placement to the platform/window manager after sizing the app. On some monitor arrangements this could put the top frame/title bar above the available desktop area, making the window hard to recover interactively.

## Window geometry clamp/centering strategy

LCD-5F adds safe startup geometry helpers in `v3_app/app.py`:

- `safe_initial_window_geometry(...)` clamps a desired size and optional top-left point to the primary screen `availableGeometry()`.
- `clamp_window_to_available_screen(...)` applies that safe geometry to a `QMainWindow`.
- Initial app geometry is centered inside the available screen area and scaled down when the desired size is larger than the available desktop.

The strategy uses Qt available geometry rather than raw screen geometry, so taskbar/menu-bar reserved areas are accounted for when Qt reports them.

## Reset-window-geometry option

LCD-5F adds `--reset-window-geometry` and `HELMFORGE_RESET_WINDOW_GEOMETRY=1`. The flag is forwarded through `v3_app.main` into `build_window(...)` and recorded on the window as reset geometry intent. No unrelated settings are persisted.

## Mapping read-only clarification

The HOTAS Map now states that it is a read-only map for selection and inspection. The hero and inspector explicitly say:

- select controls to inspect routes
- workspace routes are not edited on this page
- editing arrives in Mapping / Route Details
- Output Intent is shown without performing a vJoy write here

## Selected-control interaction clarification

Marker clicks still update only selected marker state, selected control inspector, and route flow. They do not mutate workspace mappings, write runtime state, poll hardware, or imply output proof.

## Route editing deferral statement

LCD-5F adds a disabled affordance for `Edit route details - pending` with a `mapping.route_details` route target marker. It is intentionally not wired as an editor. It communicates where route editing belongs without implementing editing.

## Advanced Route Details density reduction strategy

The HOTAS Map no longer renders the full route record list directly. Advanced Route Details now shows:

- compact route counts
- selected route detail
- a short preview of additional routes
- a note that the full route table belongs in Mapping / Advanced Route Tables
- a disabled `Open Advanced Route Tables - pending` affordance

The full route data remains in the `MappingCommandModel` for future pages.

## What remains for Mapping / Route Details

The `mapping.route_details` route remains a future placeholder. Real route editing, safe draft mutation, route-specific controls, apply/revert behavior, and save semantics are deferred.

## What remains for Mapping / Advanced Route Tables

The `mapping.advanced_route_tables` route remains a future placeholder. Full route table browsing, filtering, grouping, and advanced diagnostics are deferred to that route.

## Runtime truth preservation statement

LCD-5F is a usability/layout correction only. It does not change runtime authority, hardware polling, vJoy write behavior, output verification logic, Full Live Runtime Ready logic, Bridge lifecycle ownership, Bridge auto-start/stop behavior, recorder capture/encoding claims, simulation fallback truth, telemetry proof rules, or workspace save/apply semantics.

## Explicit non-goals preserved

- no real route editing was implemented unless already existing safe route-switching only
- no workspace mapping mutation was added
- no hardware polling was added
- no vJoy/output behavior was changed
- no output verification behavior was changed
- no Bridge lifecycle management was added
- no recorder capture/encoding was added
- no cloud AI/LLM behavior was added
- no auto-save was added
- no animations/page transitions/radial menu/real blur were added
