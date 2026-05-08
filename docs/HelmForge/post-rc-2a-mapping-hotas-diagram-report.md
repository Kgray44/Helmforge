# HelmForge Post-RC 2A Mapping HOTAS Diagram Report

## Scope

Post-RC 2A adds the Mapping page HOTAS Diagram foundation only. It is a read-only visual/diagnostic surface for physical control layout, workspace mapping routes, and output intent labels.

## diagram approach chosen

The first implementation uses a stylized schematic instead of a photo asset. This keeps the feature shippable without external image dependencies while still showing throttle side, stick side, base region, axis markers, button markers, and the Hat / POV marker in the existing dark premium theme.

The diagram widget paints the throttle/stick/base surfaces and overlays compact marker labels. Marker hover tooltips provide the detailed route information.

## controls represented

The model represents:

- physical reference regions: throttle side, stick side, and base;
- axes: Roll axis, Pitch axis, Throttle axis, Yaw axis, Aux 1, and Aux 2;
- HOTAS buttons B1-B15;
- Hat / POV.

Each control region includes a stable control id, display label, control type, normalized anchor coordinates, optional region size, raw input channel, mapped function, output intent target, current value or state when available, help text, and mapped/unmapped/reference status.

## mapping data used

The diagram is built from the current workspace mapping config:

- axis routes provide raw axis channel, logical output, and output intent axis;
- button routes provide HOTAS button to intended virtual button routing;
- hat routes provide HOTAS hat to intended POV and optional directional button routing;
- existing Mapping page snapshot values provide current simulation/fallback values;
- already supplied fresh physical input snapshots, when present, provide read-only current axis/button/hat state.

Unavailable or missing routes are labeled as unmapped or unavailable. The diagram does not invent alternate routes when workspace mapping data exists.

## UI placement

The Mapping page now includes a HOTAS Diagram card after the Routing Overview / Live Route Summary row and before Runtime Setup / Preflight. The card includes the requested description: "See the physical controls, current mappings, and output intent targets in one visual layout."

This placement keeps the visual summary near the top without replacing the detailed routing tables. The card is scroll-safe inside the existing Mapping page layout.

## deferred to Post-RC 2B

Deferred work:

- click-to-edit or drag-to-remap interactions;
- richer selection panels and advanced diagram interaction;
- image/photo-backed HOTAS assets;
- parameter metadata/info icon integration;
- real Flight Recorder backend work;
- Help / Docs overhaul;
- output verification changes;
- Bridge lifecycle management.

## runtime truth preservation

The HOTAS Diagram is read-only and diagnostic. Telemetry remains the truth surface. It keeps no hardware polling, no vJoy writes, no output verification, no Bridge start/stop/restart behavior, no runtime authority, and no Full Live Runtime Ready logic changes.

The diagram uses wording such as physical layout reference, mapping intent, output intent, simulation/fallback value, and read-only visual/diagnostic diagram. output intent is not output write proof, vJoy detected is not output verification, physical input alone is not Full Live Runtime Ready, fake/test paths are not real readiness, packaged smoke is not runtime readiness, and simulation mode remains available.
