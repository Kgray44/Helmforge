from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LiquidSubpage:
    subpage_id: str
    display_name: str
    purpose: str
    route_key: str
    parent_mode_id: str
    availability_state: str = "placeholder"
    tooltip: str = ""
    accessibility_text: str = ""


@dataclass(frozen=True)
class LiquidMode:
    mode_id: str
    display_name: str
    glyph: str
    short_description: str
    accent_role: str
    subpages: tuple[LiquidSubpage, ...]
    default_subpage_id: str
    tooltip: str = ""
    accessibility_text: str = ""
    route_prefix: str = ""

    @property
    def default_subpage(self) -> LiquidSubpage:
        return self.subpage_by_id(self.default_subpage_id)

    @property
    def label(self) -> str:
        return self.display_name

    @property
    def purpose(self) -> str:
        return self.short_description

    def subpage_by_id(self, subpage_id: str) -> LiquidSubpage:
        for subpage in self.subpages:
            if subpage.subpage_id == subpage_id:
                return subpage
        raise KeyError(subpage_id)


@dataclass(frozen=True)
class LiquidRoute:
    route_key: str
    mode_id: str
    subpage_id: str
    mode_display_name: str
    subpage_display_name: str
    purpose: str
    availability_state: str
    accent_role: str


@dataclass(frozen=True)
class LiquidNavigationModel:
    modes: tuple[LiquidMode, ...]
    _modes_by_id: dict[str, LiquidMode] = field(init=False, repr=False)
    _routes_by_key: dict[str, LiquidRoute] = field(init=False, repr=False)
    _routes_by_mode_subpage: dict[tuple[str, str], LiquidRoute] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        modes_by_id: dict[str, LiquidMode] = {}
        routes_by_key: dict[str, LiquidRoute] = {}
        routes_by_mode_subpage: dict[tuple[str, str], LiquidRoute] = {}

        for mode in self.modes:
            if mode.mode_id in modes_by_id:
                raise ValueError(f"Duplicate Liquid mode id: {mode.mode_id}")
            modes_by_id[mode.mode_id] = mode
            seen_subpages: set[str] = set()
            for subpage in mode.subpages:
                if subpage.parent_mode_id != mode.mode_id:
                    raise ValueError(f"{subpage.route_key} is attached to the wrong mode")
                if subpage.subpage_id in seen_subpages:
                    raise ValueError(f"Duplicate Liquid subpage id in {mode.mode_id}: {subpage.subpage_id}")
                if subpage.route_key in routes_by_key:
                    raise ValueError(f"Duplicate Liquid route key: {subpage.route_key}")
                seen_subpages.add(subpage.subpage_id)
                route = LiquidRoute(
                    route_key=subpage.route_key,
                    mode_id=mode.mode_id,
                    subpage_id=subpage.subpage_id,
                    mode_display_name=mode.display_name,
                    subpage_display_name=subpage.display_name,
                    purpose=subpage.purpose,
                    availability_state=subpage.availability_state,
                    accent_role=mode.accent_role,
                )
                routes_by_key[route.route_key] = route
                routes_by_mode_subpage[(route.mode_id, route.subpage_id)] = route
            mode.subpage_by_id(mode.default_subpage_id)

        object.__setattr__(self, "_modes_by_id", modes_by_id)
        object.__setattr__(self, "_routes_by_key", routes_by_key)
        object.__setattr__(self, "_routes_by_mode_subpage", routes_by_mode_subpage)

    @property
    def mode_ids(self) -> tuple[str, ...]:
        return tuple(mode.mode_id for mode in self.modes)

    @property
    def routes(self) -> tuple[LiquidRoute, ...]:
        return tuple(self._routes_by_key.values())

    @property
    def default_mode(self) -> LiquidMode:
        return self.modes[0]

    @property
    def default_route(self) -> LiquidRoute:
        mode = self.default_mode
        return self.route_for(mode.mode_id, mode.default_subpage_id)

    def mode_by_id(self, mode_id: str) -> LiquidMode:
        try:
            return self._modes_by_id[mode_id]
        except KeyError as exc:
            raise KeyError(mode_id) from exc

    def route_by_key(self, route_key: str) -> LiquidRoute:
        try:
            return self._routes_by_key[route_key]
        except KeyError as exc:
            raise KeyError(route_key) from exc

    def route_for(self, mode_id: str, subpage_id: str) -> LiquidRoute:
        try:
            return self._routes_by_mode_subpage[(mode_id, subpage_id)]
        except KeyError as exc:
            raise KeyError(f"{mode_id}.{subpage_id}") from exc


@dataclass
class LiquidNavigationState:
    model: LiquidNavigationModel
    current_mode_id: str = ""
    current_subpage_id: str = ""
    last_subpage_by_mode: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.current_mode_id:
            self.current_mode_id = self.model.default_mode.mode_id
        mode = self.model.mode_by_id(self.current_mode_id)
        if not self.current_subpage_id:
            self.current_subpage_id = mode.default_subpage_id
        mode.subpage_by_id(self.current_subpage_id)
        self.last_subpage_by_mode.setdefault(self.current_mode_id, self.current_subpage_id)

    @property
    def current_route(self) -> LiquidRoute:
        return self.model.route_for(self.current_mode_id, self.current_subpage_id)

    def select_mode(self, mode_id: str) -> LiquidRoute:
        mode = self.model.mode_by_id(mode_id)
        self.current_mode_id = mode.mode_id
        self.current_subpage_id = self.last_subpage_by_mode.get(mode.mode_id, mode.default_subpage_id)
        mode.subpage_by_id(self.current_subpage_id)
        self.last_subpage_by_mode[mode.mode_id] = self.current_subpage_id
        return self.current_route

    def select_subpage(self, subpage_id: str) -> LiquidRoute:
        mode = self.model.mode_by_id(self.current_mode_id)
        mode.subpage_by_id(subpage_id)
        self.current_subpage_id = subpage_id
        self.last_subpage_by_mode[self.current_mode_id] = subpage_id
        return self.current_route

    def select_route(self, route_key: str) -> LiquidRoute:
        route = self.model.route_by_key(route_key)
        self.current_mode_id = route.mode_id
        self.current_subpage_id = route.subpage_id
        self.last_subpage_by_mode[route.mode_id] = route.subpage_id
        return route


def build_liquid_navigation_model() -> LiquidNavigationModel:
    return DEFAULT_LIQUID_NAVIGATION_MODEL


def _subpage(mode_id: str, subpage_id: str, display_name: str, purpose: str) -> LiquidSubpage:
    route_key = f"{mode_id}.{subpage_id}"
    return LiquidSubpage(
        subpage_id=subpage_id,
        display_name=display_name,
        purpose=purpose,
        route_key=route_key,
        parent_mode_id=mode_id,
        availability_state="placeholder",
        tooltip=display_name,
        accessibility_text=f"{display_name} route",
    )


DEFAULT_LIQUID_NAVIGATION_MODEL = LiquidNavigationModel(
    modes=(
        LiquidMode(
            mode_id="preflight",
            display_name="Preflight",
            glyph="▲",
            short_description="Confirm setup, runtime boundaries, and readiness blockers.",
            accent_role="warning",
            route_prefix="preflight",
            default_subpage_id="command_readiness",
            tooltip="Preflight",
            accessibility_text="Preflight",
            subpages=(
                _subpage(
                    "preflight",
                    "command_readiness",
                    "Command Readiness",
                    "Can I safely use live output right now?",
                ),
            ),
        ),
        LiquidMode(
            mode_id="mapping",
            display_name="Mapping",
            glyph="◇",
            short_description="Shape physical controls into workspace and output intent.",
            accent_role="info",
            route_prefix="mapping",
            default_subpage_id="hotas_map",
            tooltip="Mapping",
            accessibility_text="Mapping",
            subpages=(
                _subpage("mapping", "hotas_map", "HOTAS Map", "What is each physical control doing?"),
                _subpage(
                    "mapping",
                    "route_details",
                    "Route Details",
                    "How does this physical control route through workspace intent?",
                ),
                _subpage(
                    "mapping",
                    "advanced_route_tables",
                    "Advanced Route Tables",
                    "What advanced route details are available for later editing?",
                ),
            ),
        ),
        LiquidMode(
            mode_id="tuning",
            display_name="Tuning",
            glyph="~",
            short_description="Tune response curves, filters, and profile behavior.",
            accent_role="info",
            route_prefix="tuning",
            default_subpage_id="base_tuning",
            tooltip="Tuning",
            accessibility_text="Tuning",
            subpages=(
                _subpage("tuning", "base_tuning", "Base Tuning", "How does this axis respond and feel?"),
                _subpage("tuning", "filtering", "Filtering", "How should noisy input be smoothed?"),
                _subpage(
                    "tuning",
                    "combat_profile",
                    "Combat Profile",
                    "How should combat response differ from baseline tuning?",
                ),
                _subpage(
                    "tuning",
                    "conditional_rules",
                    "Conditional Rules",
                    "Which rules can change the response stack, and when do they trigger?",
                ),
                _subpage(
                    "tuning",
                    "profiles_library",
                    "Profiles Library",
                    "Which workspace tuning profiles are available and what can I safely do with them?",
                ),
            ),
        ),
        LiquidMode(
            mode_id="analysis",
            display_name="Analysis",
            glyph="≋",
            short_description="Inspect signal behavior and configuration effects.",
            accent_role="success",
            route_prefix="analysis",
            default_subpage_id="effective_response_stack",
            tooltip="Analysis",
            accessibility_text="Analysis",
            subpages=(
                _subpage(
                    "analysis",
                    "effective_response_stack",
                    "Effective Response Stack",
                    "How does raw input become final output?",
                ),
                _subpage("analysis", "live_monitor", "Live Monitor", "What is the HOTAS doing right now?"),
            ),
        ),
        LiquidMode(
            mode_id="recorder",
            display_name="Recorder",
            glyph="●",
            short_description="Review recorder surfaces without claiming capture authority.",
            accent_role="warning",
            route_prefix="recorder",
            default_subpage_id="flight_recorder",
            tooltip="Recorder",
            accessibility_text="Recorder",
            subpages=(
                _subpage("recorder", "flight_recorder", "Flight Recorder", "What can I capture, buffer, and review?"),
                _subpage(
                    "recorder",
                    "clip_library",
                    "Clip Library / Artifacts",
                    "What metadata-only artifacts are available for review?",
                ),
                _subpage(
                    "recorder",
                    "capture_backend_truth",
                    "Capture Backend Truth",
                    "What can I capture, buffer, and review?",
                ),
            ),
        ),
        LiquidMode(
            mode_id="support",
            display_name="Support",
            glyph="?",
            short_description="Find Help, diagnostics, and runtime setup guidance.",
            accent_role="info",
            route_prefix="support",
            default_subpage_id="help_docs",
            tooltip="Support",
            accessibility_text="Support",
            subpages=(
                _subpage(
                    "support",
                    "help_docs",
                    "Help / Docs",
                    "How do I understand and use this page or parameter?",
                ),
                _subpage("support", "perf_diagnostics", "Perf / Diagnostics", "What is the system actually reporting?"),
                _subpage(
                    "support",
                    "setup_runtime_check",
                    "Setup / Runtime Check",
                    "What is the system actually reporting?",
                ),
            ),
        ),
    )
)
