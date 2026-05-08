from __future__ import annotations

from dataclasses import dataclass

from v3_app.services.parameter_metadata import PARAMETER_HELP, ParameterMetadata


HELP_CATEGORY_ORDER = (
    "Advanced Pages",
    "Analysis",
    "Core Pages",
    "Diagnostics",
    "Getting Started",
    "Reference",
    "Workflow",
)

HELP_TOPIC_TREE_ORDER = (
    "Getting Started",
    "Runtime Truth",
    "Mapping",
    "Tuning",
    "Filtering",
    "Combat Profile",
    "Modes",
    "Conditional Rules",
    "Effective Response Stack",
    "Live Monitor",
    "Live Overlay",
    "Flight Recorder",
    "Helm Assistant",
    "Profiles",
    "Perf / Diagnostics",
    "Packaging / Setup",
    "Troubleshooting",
    "Parameter Reference",
)

HELP_SORT_OPTIONS = (
    "By Category",
    "By Last Opened",
    "Alphabetical A-Z",
    "Alphabetical Z-A",
    "By Importance",
)


@dataclass(frozen=True)
class HelpArticleSection:
    heading: str
    body: tuple[str, ...]

    @property
    def text(self) -> str:
        return "\n".join((self.heading, *self.body))


@dataclass(frozen=True)
class HelpArticle:
    title: str
    category: str
    summary: str
    paragraphs: tuple[str, ...]
    keywords: tuple[str, ...] = ()
    related_topics: tuple[str, ...] = ()
    sections: tuple[HelpArticleSection, ...] = ()
    topic_category: str | None = None
    open_page_id: str | None = None
    parameter_ids: tuple[str, ...] = ()
    importance: int = 50

    @property
    def body(self) -> str:
        section_text = tuple(section.text for section in self.sections)
        return "\n\n".join((*self.paragraphs, *section_text))

    @property
    def search_text(self) -> str:
        parameter_text = " ".join(
            PARAMETER_HELP.require(parameter_id).display_name
            for parameter_id in self.parameter_ids
            if PARAMETER_HELP.get(parameter_id) is not None
        )
        return " ".join((self.title, self.category, self.summary, " ".join(self.keywords), parameter_text, self.body))


@dataclass(frozen=True)
class HelpSearchResult:
    article: HelpArticle
    score: int


def all_articles() -> tuple[HelpArticle, ...]:
    return (*ARTICLES, *AUXILIARY_ARTICLES, *POST_RC_1D_ARTICLES)


def articles_by_category() -> dict[str, tuple[HelpArticle, ...]]:
    grouped: dict[str, list[HelpArticle]] = {category: [] for category in HELP_CATEGORY_ORDER}
    for article in ARTICLES:
        grouped.setdefault(article.category, []).append(article)
    return {category: tuple(grouped.get(category, ())) for category in HELP_CATEGORY_ORDER}


def get_article(title: str) -> HelpArticle:
    normalized = _normalize(title)
    for article in all_articles():
        if _normalize(article.title) == normalized:
            return article
    raise KeyError(title)


def search_articles(query: str) -> tuple[HelpSearchResult, ...]:
    terms = tuple(term for term in _normalize(query).split() if term)
    if not terms:
        return tuple(HelpSearchResult(article=article, score=0) for article in ARTICLES)

    results: list[HelpSearchResult] = []
    for article in all_articles():
        haystack = _normalize(article.search_text)
        if not all(term in haystack for term in terms):
            continue
        score = 0
        for term in terms:
            score += 1
            if term in _normalize(article.title):
                score += 4
            if term in _normalize(" ".join(article.keywords)):
                score += 2
        if score:
            results.append(HelpSearchResult(article=article, score=score))
    return tuple(
        sorted(
            results,
            key=lambda result: (
                -result.score,
                _category_sort_index(result.article.category),
                result.article.title,
            ),
        )
    )


def topic_tree_by_category(
    articles: tuple[HelpArticle, ...] | None = None,
    *,
    sort_mode: str = "By Category",
    last_opened: dict[str, int] | None = None,
) -> dict[str, tuple[HelpArticle, ...]]:
    grouped: dict[str, list[HelpArticle]] = {category: [] for category in HELP_TOPIC_TREE_ORDER}
    for article in articles or all_articles():
        grouped.setdefault(topic_category_for(article), []).append(article)
    return {
        category: tuple(sort_help_articles(tuple(grouped.get(category, ())), sort_mode, last_opened=last_opened))
        for category in HELP_TOPIC_TREE_ORDER
        if grouped.get(category)
    }


def sort_help_articles(
    articles: tuple[HelpArticle, ...],
    sort_mode: str,
    *,
    last_opened: dict[str, int] | None = None,
) -> tuple[HelpArticle, ...]:
    if sort_mode == "Alphabetical Z-A":
        return tuple(sorted(articles, key=lambda article: article.title.casefold(), reverse=True))
    if sort_mode == "Alphabetical A-Z":
        return tuple(sorted(articles, key=lambda article: article.title.casefold()))
    if sort_mode == "By Importance":
        return tuple(sorted(articles, key=lambda article: (-article.importance, article.title.casefold())))
    if sort_mode == "By Last Opened":
        opened = last_opened or {}
        return tuple(sorted(articles, key=lambda article: (-opened.get(article.title, -1), article.title.casefold())))
    return tuple(sorted(articles, key=lambda article: (-article.importance, article.title.casefold())))


def topic_category_for(article: HelpArticle) -> str:
    if article.topic_category:
        return article.topic_category
    if article.title in {"Quick Start", "Simulation mode", "HelmForge overview"}:
        return "Getting Started"
    if article.title in {
        "Runtime Setup / vJoy Setup",
        "Runtime Indicators",
        "Full Live Runtime Ready",
        "vJoy/output verification",
        "Bridge telemetry",
    }:
        return "Runtime Truth"
    if article.title in {"Mapping", "HOTAS diagram", "Mapping Route Inspector", "Mapping edit workflow", "Axis routing", "Button routing", "Hat routing"}:
        return "Mapping"
    if article.title in {"Base Tuning", "Tuning Glossary", "Curve modes", "Deadzone / anti-deadzone", "Hysteresis", "Output scale / max output"}:
        return "Tuning"
    if article.title in {"Filtering", "Slew limits"}:
        return "Filtering"
    if article.title == "Combat Profile":
        return "Combat Profile"
    if article.title in {"Modes", "Precision mode", "Combat mode", "Stack mode"}:
        return "Modes"
    if article.title in {"Conditional Rules", "Rule stages", "Comparators"}:
        return "Conditional Rules"
    if article.title == "Effective Response Stack":
        return "Effective Response Stack"
    if article.title == "Live Monitor":
        return "Live Monitor"
    if article.title == "Live Overlay":
        return "Live Overlay"
    if article.title.startswith("Flight Recorder") or article.title in {
        "Recorder review/export diagnostics",
        "One-frame capture proof",
        "Real capture limitations",
    }:
        return "Flight Recorder"
    if article.title == "Helm":
        return "Helm Assistant"
    if article.title == "Profiles":
        return "Profiles"
    if article.title == "Performance / Diagnostics":
        return "Perf / Diagnostics"
    if article.title.startswith("Packaging"):
        return "Packaging / Setup"
    if article.title == "Troubleshooting":
        return "Troubleshooting"
    if article.title == "Parameter Reference":
        return "Parameter Reference"
    return "Getting Started"


def parameter_reference_entries(*, category: str | None = None) -> tuple[ParameterMetadata, ...]:
    entries = PARAMETER_HELP.all()
    if category is not None:
        entries = tuple(entry for entry in entries if entry.category == category)
    return tuple(sorted(entries, key=lambda entry: (entry.category, entry.section, entry.display_name)))


def _category_sort_index(category: str) -> int:
    try:
        return HELP_CATEGORY_ORDER.index(category)
    except ValueError:
        return len(HELP_CATEGORY_ORDER)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().replace("/", " ").replace("-", " ").split())


ARTICLES = (
    HelpArticle(
        title="Conditional Rules",
        category="Advanced Pages",
        summary="Build conditional tuning changes that inject at known response-stack stages.",
        keywords=("rules", "injection", "yaw", "roll", "output scale"),
        related_topics=("Effective Response Stack", "Runtime Indicators", "Helm"),
        paragraphs=(
            "Conditional Rules let the workspace describe draft rules such as changing one axis parameter when another axis crosses a threshold. Rules have a target axis, parameter, operation, value, injection stage, mode gate, reference axis, reference stage, measure, comparator, and threshold.",
            "Rules are evaluated by shared_core and shown in the UI as active, inactive, blocked, or disabled. Disabled rules do not apply. Invalid rules report blocked or validation state and do not crash the pipeline.",
            "Use this page for configuration and inspection only. The UI does not poll hardware or write vJoy. Future Bridge telemetry can report live rule state, but Phase 11A Help / Docs only explains the model.",
        ),
    ),
    HelpArticle(
        title="Effective Response Stack",
        category="Advanced Pages",
        summary="Inspect one axis through raw input, shaping, filtering, modes, rule injection, and final output.",
        keywords=("response", "stack", "pipeline", "raw", "final", "graph"),
        related_topics=("Graphs and Previews", "Conditional Rules", "Runtime Indicators"),
        paragraphs=(
            "Effective Response Stack is the diagnostic page that explains why an axis feels the way it does. It visualizes recovered stages: Raw Input, Center Conditioning, Curve / Shape, Base Output Limits, Filtering, Mode Modifiers, Rule Injections, and Final Output.",
            "The Raw vs Final graph uses a true linear reference and processed response curve. Stage cards are updated in place to avoid the old twitch behavior from rebuilding widgets on every update.",
            "Rules appear through shared rule injection metadata at their actual stack context. If stack data is simulated or unavailable, the page and Help / Docs should say so plainly instead of implying live hardware analysis. In Phase 14, physical input samples may feed a read-only stack preview when available, but the preview is diagnostic only and never writes output.",
        ),
    ),
    HelpArticle(
        title="Helm",
        category="Advanced Pages",
        summary="Use the local diagnostic assistant for staged, reversible tuning recommendations.",
        keywords=("assistant", "helm", "overlay", "in-memory", "recommendation"),
        related_topics=("Runtime Indicators", "Saving and Importing", "Tuning Glossary"),
        paragraphs=(
            "Helm launches from the top-right ASSISTANT cluster. Helm is an overlay/modal, not a sidebar page, so it can help without moving the user away from the current workspace.",
            "Helm is deterministic and local. It does not use cloud AI or LLM behavior. It reads workspace values, mode settings, conditional rule summaries, optional response stack snapshots, and runtime diagnostic context when available, then labels the evidence it used.",
            "Helm recommendations are staged before apply. Apply Selected Changes modifies only the in-memory workspace draft. Save Workspace remains the only persistence action. Revert Last Helm Changes restores the last applied Helm batch.",
            "Helm does not mutate conditional rules in v1 and does not perform live hardware analysis. If runtime truth says blocked_missing_device or output verification is false, Helm treats changes as draft tuning guidance only.",
        ),
    ),
    HelpArticle(
        title="Graphs and Previews",
        category="Analysis",
        summary="Read local response previews without confusing them for verified output writes.",
        keywords=("graphs", "preview", "raw", "final", "curve"),
        related_topics=("Effective Response Stack", "Runtime Indicators", "Base Tuning"),
        paragraphs=(
            "Graphs and previews show how the current workspace math is expected to transform input. They help compare raw input, shaped response, filtered response, and final output from the shared-core pipeline.",
            "A graph can be useful even in simulation mode, but it is not proof that a physical HOTAS is being polled or that vJoy output writes are verified. Treat graph values as workspace or telemetry evidence depending on the source label.",
            "Phase 12A adds Live Overlay core/config foundations, and Phase 12B adds an app-owned detached overlay window and renderer. Overlay traces can use simulation or runtime snapshot values already available to the UI, but they do not prove live hardware, vJoy writes, or output verification.",
            "Live Overlay is app-owned and detached. It does not inject into games, does not use graphics API hooking, and does not capture the screen. Hotkey and click-through statuses are truth-labeled; they are not claimed unless implemented and verified. Flight Recorder is a separate later phase.",
            "Phase 13A adds Flight Recorder UI/state/settings/library/preview shell only. Phase 13B adds recorder backend interfaces, telemetry hindsight buffering, a missing backend, an injected simulated backend, and clearly labeled simulated non-video JSON manifests. Phase 13C adds a simulated compositor/exporter that writes metadata and overlay trace bundles, not recordings. Phase 13D finalizes the library and metadata-only preview: simulated exports are not real recordings, no screen capture or video encoding is implemented, telemetry hindsight is separate from video hindsight, Live Overlay colors and traces are reused, Ctrl+Shift+F10 is configured as recorder hotkey text but not registered, and Phase 14 is real HOTAS input, not recorder capture. For Phase 13 boundaries, real capture and encoding are deferred, and hindsight video buffering is deferred.",
            "When a graph is backed by simulation, the UI should say Simulation Fallback or a similar truthful status. When Bridge telemetry is fresh, the graph can consume Bridge-provided values while still respecting output_verified truth.",
        ),
    ),
    HelpArticle(
        title="Runtime Indicators",
        category="Analysis",
        summary="Understand the exact runtime truth terms used across HelmForge.",
        keywords=("runtime", "telemetry", "truth", "stale", "missing", "invalid", "bridge"),
        related_topics=("Runtime Setup / vJoy Setup", "Performance / Diagnostics", "Live Monitor", "Effective Response Stack"),
        paragraphs=(
            "Telemetry remains the truth surface for Bridge-reported runtime state. Bridge lifecycle describes the Bridge state such as Simulated, Starting, Stopping, or future live states. Runtime truth is the typed status, for example blocked_missing_device or detected_unverified.",
            "Output verified means actual output writes have been proven by a guarded verification/write path. Full Live Runtime Ready means both input and output are proven. In the final Phase 15D boundary, output_verified remains false in normal runtime unless guarded real verification succeeds, and Full Live Runtime Ready remains false unless Phase 16 end-to-end runtime conditions prove both sides.",
            "Runtime orchestrator is the Phase 16 contract that can build compact runtime frames from simulation or guarded physical input, run the shared workspace pipeline, produce final output intent, and report output-loop truth. In Phase 16A, the simulation path is complete and output intent remains separate from output write proof.",
            "Runtime frame is the Phase 16B telemetry surface for compact orchestrator truth. It can show input source, pipeline status, final output intent summary, output loop state, output_verified, Full Live Runtime Ready, runtime truth, blocked reason, warnings, and errors without dumping full internal stack objects.",
            "Phase 16C connects the verified input/output path semantics. physical input, pipeline, output verification, and output loop are separate proofs. fake/test path does not equal real hardware readiness. Phase 16D owns the final readiness gate, so Full Live Runtime Ready remains false in Phase 16C while verified_runtime_candidate can describe a fully proven candidate path.",
            "Phase 16D centralizes the Full Live Runtime Ready gate. Full Live Runtime Ready means fresh physical input, successful pipeline processing, guarded real output verification, explicit output loop enable/running according to policy, fresh Bridge telemetry/runtime_frame, and no safety stop or blocking errors. physical input alone is not enough, output verification alone is not enough, output loop running alone is not enough, fake/test paths are not real readiness, and stale telemetry blocks readiness.",
            "Phase 17A is product polish, layout QA, and UI consistency only. It keeps the Phase 16 readiness gate intact while tightening page spacing, status chip/action button distinction, recorder truth copy, overlay dialog sizing, and output-intent terminology.",
            "Phase 17B is motion, interaction smoothness, and performance polish only. It reuses page instances, records shared page-switch/update timing, counts hidden Live Monitor and Effective Response Stack skips, keeps graph items updated in place instead of rebuilding plots, and confirms Live Overlay timers stop when hidden. These timing and skip fields are app diagnostics, not hardware or output proof.",
            "Phase 17C completes Product Polish, Layout QA, and Motion with final product QA and a report-only Phase 18 readiness census. It does not implement packaging, installer scripts, icon conversion, user data migration, hardware polling, vJoy writes, output verification changes, Bridge lifecycle management, recorder capture or encoding, auto-save, or runtime activation. Phase 18 is Packaging, Installer, Icons, and User Data Locations and must preserve simulation mode and runtime truth behavior.",
            "Phase 18A adds packaging foundation, a dry-run build script, PyInstaller one-folder planning, Inno Setup handoff notes, and LocalAppData user data path helpers. It does not implement a full installer, driver installer launch, Bridge lifecycle management, runtime behavior, hardware polling, vJoy/output behavior changes, or output verification changes.",
            "Phase 18C adds an Inno Setup installer script, Start Menu shortcut definition, optional Desktop shortcut task, optional launch-after-install task, uninstall metadata, and optional installer compile support. It does not install drivers, install virtual-output software, manage Bridge lifecycle, or change runtime truth.",
            "Phase 18D completes Packaging, Installer, Icons, and User Data Locations with final QA, one-folder smoke verification, installer metadata review, user-data separation checks, and Phase 19 readiness notes. Phase 18D does not add runtime authority.",
            "Virtual output backend, Virtual output backend kind, Virtual output backend status, vJoy dependency, vJoy device, output device status, output write status, output verification status, output verification source, Fake output verified, Real output verified, Last verification timestamp, Output loop state, write count, failure count, last output write, neutral restore status, and safety stop reason describe the Phase 15 output surface. vJoy detected does not equal output verified, output intent is not a write, fake/mock verification is not real vJoy verification, and the output loop requires verified backend proof before it can write.",
            "HOTAS discovery and Device discovery are read-only identity checks. Physical input backend, Supported HOTAS, Selected input device, Input sampling, Physical input sample, Read-only input sampling, Sample source, Sample age, and Physical input read-only are device-selection and read-only sampling truth fields; they do not prove vJoy output or live runtime readiness. Physical input sampling active means raw input can be read, not that output is verified. Process hint is only a diagnostic hint and never becomes runtime truth. Command acknowledgement means Bridge telemetry has a matching request_id for the latest UI command request.",
            "Stale telemetry is too old to treat as fresh. Missing telemetry means the file is not present. Invalid telemetry means the JSON could not be parsed or validated. Simulation fallback keeps the UI usable when telemetry is stale, missing, or invalid, and stale/error/unavailable physical input falls back safely.",
        ),
    ),
    HelpArticle(
        title="Base Tuning",
        category="Core Pages",
        summary="Adjust the underlying axis shape before mode-specific layers are applied.",
        keywords=("base", "curve", "deadzone", "anti-deadzone", "output scale"),
        related_topics=("Filtering", "Combat Profile", "Tuning Glossary"),
        paragraphs=(
            "Base Tuning controls the first user-facing shaping layer for each axis. Curve strength changes how quickly an axis grows away from center. Deadzone ignores tiny center movement. Anti-deadzone restores a controlled minimum response after the deadzone.",
            "Output scale and max output limit how much authority the axis can produce before later mode and rule layers. These settings should be adjusted in small steps because they affect every mode built on top of the axis.",
            "Base Tuning is configuration work. It does not write to vJoy and does not verify output writes. Save Workspace is required to persist edits to the V3 workspace file.",
        ),
    ),
    HelpArticle(
        title="Combat Profile",
        category="Core Pages",
        summary="Tune combat-specific damping, slew, curve, and scale behavior.",
        keywords=("combat", "scale", "center alpha", "slew", "trigger"),
        related_topics=("Modes", "Filtering", "Helm"),
        paragraphs=(
            "Combat Profile adjusts how an axis behaves when combat-related mode gates are active. Combat scale controls authority, combat center and edge alpha affect smoothing, and same/reverse slew values shape direction changes.",
            "These values can make aiming steadier, faster, or less abrupt, but they can also compound with Precision mode when the stack mode is multiply. Helm can flag that context and keep recommendations moderate.",
            "Combat Profile edits are draft workspace edits. They are not live runtime activation, not physical input polling, and not output verification.",
        ),
    ),
    HelpArticle(
        title="Filtering",
        category="Core Pages",
        summary="Tune smoothing and directional slew limits for each axis.",
        keywords=("filtering", "center alpha", "edge alpha", "slew", "hysteresis"),
        related_topics=("Base Tuning", "Combat Profile", "Tuning Glossary"),
        paragraphs=(
            "Filtering controls how quickly the processed signal follows the shaped input. Center alpha affects small movements near center, edge alpha affects larger movements, and slew limits cap how quickly the signal can change in the same or reverse direction.",
            "Higher smoothing can make control calmer, but too much can feel delayed. Low slew limits can help with jitter yet make reversals sticky. Use the graph and response stack to inspect the effect before saving.",
            "Filtering remains part of the workspace configuration path. It does not poll real hardware, stream live physical input, write vJoy, or claim output verification.",
        ),
    ),
    HelpArticle(
        title="Modes",
        category="Core Pages",
        summary="Configure precision, combat, zoom, and extra mode gates.",
        keywords=("modes", "precision", "combat", "zoom", "stack"),
        related_topics=("Combat Profile", "Runtime Indicators", "Helm"),
        paragraphs=(
            "Modes define when alternate tuning layers become active. Precision, Combat, Zoom, and Extra can each be tied to buttons and gates as the workspace evolves.",
            "Stack mode controls how mode effects combine. Multiply stacking can compound reductions, while future modes may use alternate composition. Helm can mention mode stacking as context but still applies only safe draft tuning diffs.",
            "Mode configuration is saved through the workspace. It does not start the Bridge and does not prove live runtime readiness.",
        ),
    ),
    HelpArticle(
        title="Profiles",
        category="Core Pages",
        summary="Organize workspace variants for different aircraft or control styles.",
        keywords=("profiles", "workspace", "library", "import"),
        related_topics=("Saving and Importing", "Mapping", "Quick Start"),
        paragraphs=(
            "Profiles are workspace variants that can represent different aircraft, games, or control styles. The current implementation keeps profile work conservative while the V3 schema and page behavior stabilize.",
            "A profile should be treated as configuration, not runtime proof. Loading or editing a profile changes what the workspace intends to do; Bridge telemetry and output verification still decide runtime truth.",
            "Use clear profile names and save intentionally. Import Profile is a user action and should not be confused with Bridge command requests or telemetry updates.",
        ),
    ),
    HelpArticle(
        title="Mapping",
        category="Core Pages",
        summary="Map raw HOTAS axes, buttons, and hats to the workspace output path.",
        keywords=("mapping", "axes", "buttons", "hats", "outputs"),
        related_topics=("Runtime Setup / vJoy Setup", "Saving and Importing", "Profiles"),
        paragraphs=(
            "Mapping defines how source axes, buttons, and hats are routed into the workspace output model. It is the foundation for later tuning, filtering, modes, and conditional rules.",
            "Mapping edits update the in-memory workspace draft and can be saved to `hotas_bridge_config_v3.json`. The page can show simulation, telemetry-backed values, or read-only physical samples. Mapping can label Live Raw values as physical input samples when a fresh physical sample is available, but mapping itself does not write vJoy and final output is not written to vJoy in Phase 14.",
            "Mapping can show runtime frame source, pipeline status, output intent readiness, output backend, and output loop state from Phase 16B telemetry when runtime_frame is available. Phase 16C adds input proof, pipeline proof, output proof, runtime candidate, and compact proof summary fields. Phase 16D adds Ready state, Telemetry proof, Safety proof, Fake/real path, readiness evaluation time, and Full Live Runtime Ready gate fields. Those fields describe orchestrated runtime truth; output intent ready does not mean vJoy output was written.",
            "If the physical HOTAS is missing, mapping can still be edited safely. Runtime truth may remain blocked_missing_device until runtime_frame proof shows fresh physical input, successful pipeline processing, guarded real output verification, enabled output-loop state, and fresh telemetry.",
        ),
    ),
    HelpArticle(
        title="Performance / Diagnostics",
        category="Diagnostics",
        summary="Inspect app timing, runtime truth, Bridge telemetry, and safe preflight visibility.",
        keywords=("performance", "diagnostics", "perf", "phase 11b", "timings", "preflight"),
        related_topics=("Runtime Indicators", "Runtime Setup / vJoy Setup"),
        paragraphs=(
            "Performance / Diagnostics is the diagnostics half of Phase 11. Diagnostics are observational and read-only. The page surfaces runtime truth, telemetry freshness, Bridge lifecycle, HOTAS discovery, Phase 14 physical input backend/device-selection/sampling truth, Phase 15 virtual output backend kind/status, guarded verification truth, Output loop state, output loop fields, Phase 16 runtime orchestrator truth when surfaced, simulation fallback state, output verification truth, workspace state, and lightweight UI timing metrics.",
            "Runtime frame diagnostics include availability, sequence, source, pipeline status, output intent readiness, output backend, output loop state, last output write status, output_verified, Full Live Runtime Ready, runtime truth, blocked reason, warnings, and errors. Runtime path proof includes input proof, pipeline proof, output proof, Full Live Runtime Ready gate, ready state, telemetry proof, safety proof, fake/real path, readiness evaluation time, runtime candidate, output-loop enabled/running/safety-stopped fields, and compact proof summary.",
            "Run Runtime Preflight is safe and does not verify output. It refreshes preflight truth but does not install drivers, launch installers, start the Bridge, poll live HOTAS input, write virtual output, verify output, or activate runtime.",
            "timing metrics are app/UI diagnostics, not live hardware proof. hidden-page skip counters show skipped expensive updates where instrumented, and unavailable counters are labeled truthfully.",
            "Phase 17B shares the diagnostics collector across Shell, Live Monitor, Effective Response Stack, and Perf / Diagnostics so page-switch timing, heartbeat timing, graph update timing, and hidden-page skip counters describe the same app session. Graph previews update line data in place to avoid flicker and rebuild churn, while detached Live Overlay refresh stops when the overlay is hidden. These fields are not hardware or output proof and do not change vJoy writes.",
            "Copy Diagnostics creates local diagnostic text and includes Virtual output backend, Virtual output backend kind, Virtual output backend status, vJoy dependency, vJoy device, Output verification status, Output verification source, Fake output verified, Real output verified, Last verification timestamp, output loop fields, neutral restore status, output_verified, Full Live Runtime Ready, and Full Live Runtime Ready gate proof. output_verified remains false until guarded verification proves writes, and Full Live Runtime Ready opens only when the final proof chain passes.",
            "Process presence remains a hint and telemetry remains the truth surface.",
        ),
    ),
    HelpArticle(
        title="Quick Start",
        category="Getting Started",
        summary="Start safely in simulation, edit the workspace, inspect previews, then save intentionally.",
        keywords=("quick start", "start", "simulation", "save"),
        related_topics=("Runtime Setup / vJoy Setup", "Mapping", "Saving and Importing"),
        paragraphs=(
            "Start in simulation mode. HelmForge can open, edit mappings, tune axes, inspect response previews, and use Helm recommendations without physical HOTAS hardware or output verification.",
            "Pick Mapping first, confirm the intended source and output routes, then adjust Base Tuning, Filtering, Combat Profile, Modes, and Conditional Rules as needed. Use Effective Response Stack and Live Monitor to inspect simulated or telemetry-backed behavior.",
            "Save Workspace when you want to keep the current draft. Do not treat simulation graphs, output intent, or vJoy detection as verified output writes.",
        ),
    ),
    HelpArticle(
        title="Runtime Setup / vJoy Setup",
        category="Getting Started",
        summary="Understand simulation mode, Bridge telemetry, missing HOTAS, vJoy detection, and output verification truth.",
        keywords=("runtime", "setup", "vjoy", "bridge", "preflight", "request_id", "blocked_missing_device"),
        related_topics=("Runtime Indicators", "Performance / Diagnostics", "Quick Start", "Mapping"),
        paragraphs=(
            "Simulation mode works without physical HOTAS hardware. Simulation mode also works without output verification. This lets the UI, workspace model, graphs, rules, and Helm recommendations remain useful while live hardware work is deferred.",
            "Bridge telemetry is the runtime truth surface. Manual Bridge launch remains the current lifecycle model. The manual Bridge launch command is text only: python -m bridge_app.main --run-for-ms 250. The UI does not start, stop, restart, spawn, install, or manage the Bridge.",
            "Phase 14 added physical input detection, selection, and read-only sampling. physical input sampling is read-only, simulation mode remains available, and stale/error/unavailable physical input falls back safely.",
            "Phase 14A introduces physical input detection and device selection. simulation mode remains available with no HOTAS connected, no Bridge running, and no physical input backend dependency installed. A supported HOTAS detected does not mean vJoy output is active; device selection does not write output.",
            "Phase 14B adds read-only physical input sampling and normalization. input sampling errors or disconnects fall back safely. Phase 14C makes that sample truth visible: physical samples may appear in Mapping and Live Monitor, stale or error states fall back safely, and sample stale or error states fall back safely to simulation/unavailable status.",
            "physical input sampling does not imply vJoy output, output verification, or end-to-end runtime activation. final output is not written to vJoy in Phase 14; virtual output is governed by Phase 15 backend, verification, and output-loop gates.",
            "Phase 15A adds output backend contracts, output intent models, missing/fake backend behavior, and safe fake output verification for tests. output intent is not a write. fake/mock verification is not real vJoy verification. vJoy detected does not equal output verified, real output writes are not part of Phase 15A, output_verified remains false in normal runtime, and Full Live Runtime Ready remains false.",
            "Phase 15B adds guarded real vJoy detection and a bounded write verification path. vJoy detection is not output verification. real output verification requires guarded write success, continuous output is not active in Phase 15B, Full Live Runtime Ready remains false, simulation mode remains available, and neutral restore is attempted after a real verification write.",
            "Phase 15C adds controlled output write-loop integration. output loop requires verified backend proof and explicit enablement; vJoy detection alone is not enough. fake output loop is test/dev only. neutral restore is attempted on stop, write failures safety-stop the loop, Full Live Runtime Ready remains controlled by the Phase 16 proof gate, and simulation mode remains available.",
            "Phase 15D freezes the vJoy / Virtual Output Integration boundary. Phase 15 is now complete, and the next prompt-book phase is Phase 16: Runtime End-to-End Live Mode. output intent is not output write proof, fake/mock output is not real vJoy output, real output verification requires guarded write success plus neutral restore, output loop must be explicitly enabled and safety-gated, neutral restore is attempted on stop, write failures safety-stop the loop, Full Live Runtime Ready may remain Phase 16, and simulation mode remains available.",
            "Phase 16 begins end-to-end runtime orchestration. Phase 16A adds a runtime orchestrator contract and deterministic simulation path through input, mapping, tuning, filtering, modes, conditional rules, final VirtualOutputIntent generation, and optional fake output-loop handoff for tests. The simulation pipeline remains available, output intent is still separate from output write, output loop remains safety-gated, real output still requires Phase 15 verification plus explicit enablement, and Full Live Runtime Ready requires both input and output proof.",
            "Phase 16B adds runtime_frame telemetry and UI surfaces. runtime_frame is the compact telemetry summary of the orchestrated runtime path, runtime_frame can be simulation-backed, output intent is not necessarily an output write, output loop state must be read separately, output_verified requires real output proof, Full Live Runtime Ready requires the full proof chain, and stale/missing runtime_frame falls back safely.",
            "Phase 16C connects the verified input/output path while keeping the final readiness gate conservative. physical input, pipeline, output verification, and output loop are separate proofs. fake/test path does not equal real hardware readiness. output intent is not a write. If every proof is present, Phase 16C reports a verified_runtime_candidate while Full Live Runtime Ready remains false because Phase 16D owns the final readiness gate.",
            "Phase 16D finalizes the Full Live Runtime Ready gate. Full Live Runtime Ready requires fresh physical input, successful pipeline processing, guarded real output verification, explicit output loop enable/running according to policy, fresh Bridge telemetry/runtime_frame, and no safety stop or blocking error. It is never inferred from vJoy detection alone, physical HOTAS detection alone, output intent generation alone, fake/mock verification, fake output loop, stale telemetry, or UI process presence.",
            "Phase 17A polishes the product surface only. It does not add hardware polling, vJoy writes, output verification changes, Bridge lifecycle management, recorder capture or encoding, installer behavior, auto-save, or runtime activation. Simulation mode remains available and the Full Live Runtime Ready gate remains the authority.",
            "Phase 17B polishes interaction smoothness and performance discipline only. Page instances are reused, hidden expensive updates are skipped and counted, graph plots update existing items, and overlay timers stop when hidden. It does not add hardware polling, vJoy writes, output verification changes, Bridge lifecycle management, recorder capture or encoding, installer behavior, auto-save, packaging work, or runtime activation.",
            "Phase 17C completes the final product QA sweep and Phase 18 packaging readiness census. It documents source launch, icon, user data path, dependency, and installer handoff needs only. The installer is not implemented in Phase 17C, packaging scripts are not added, and simulation mode remains the safe launch path for missing HOTAS or vJoy states.",
            "Phase 18A adds packaging foundation only. It introduces a packaging folder, a conservative build script with `-DryRun`, PyInstaller one-folder build notes, Inno Setup handoff notes, and LocalAppData user data path helpers. It does not implement a full installer, real driver/vJoy installer launch, automatic Bridge launch, Bridge lifecycle management, or runtime activation.",
            "Phase 18B adds the real PyInstaller one-folder build path and packaged smoke command. The packaged executable path is `packaging/dist/HelmForge/HelmForge.exe`, and the smoke command is `packaging/dist/HelmForge/HelmForge.exe --smoke-exit-ms 250`. It does not create an installer, add shortcuts, install drivers, or add Bridge lifecycle management.",
            "Phase 18C adds installer metadata only: `packaging/inno/helmforge.iss`, Start Menu shortcut, optional Desktop shortcut, optional launch after install, uninstall metadata, and optional Inno Setup compile support. It does not install drivers, install virtual-output software, launch Bridge, manage Bridge lifecycle, or change runtime readiness truth.",
            "Phase 18D freezes final packaging QA. Phase 18 is now complete, and the next prompt-book phase is Phase 19: Final Integration Kraken / Full Acceptance Sweep. Packaging success still does not prove runtime readiness, and Full Live Runtime Ready remains controlled by the Phase 16 proof gate.",
            "physical HOTAS discovery is discovery-only. A supported device discovery result does not mean vJoy writes exist or Full Live Runtime Ready has been proven. Virtual output writes remain behind Phase 15 verification and explicit output-loop gates.",
            "vJoy detected does not equal output verified. output_verified remains false until guarded verification proves writes. Full Live Runtime Ready remains false until the Phase 16 gate proves fresh input, pipeline success, real output verification, output-loop state, fresh telemetry, and safety proof. Missing HOTAS means runtime truth may be blocked_missing_device.",
            "stale, missing, or invalid telemetry falls back safely to simulation/internal telemetry. Run Preflight and Bridge commands are safe requests, not proof of runtime success. command acknowledgement requires matching request_id in fresh Bridge telemetry.",
        ),
    ),
    HelpArticle(
        title="Tuning Glossary",
        category="Reference",
        summary="Concise definitions for the tuning terms used throughout HelmForge.",
        keywords=("glossary", "definitions", "curve", "slew", "verification"),
        related_topics=("Base Tuning", "Filtering", "Combat Profile"),
        paragraphs=(
            "Curve strength changes how strongly an axis response bends away from linear. Deadzone ignores tiny input near center. Anti-deadzone adds a controlled minimum response after the deadzone. Hysteresis resists tiny direction changes so jitter does not constantly flip state.",
            "Output scale changes overall axis authority. Max output clamps the maximum possible output. Center alpha controls smoothing near center. Edge alpha controls smoothing farther from center. Same slew limit caps movement in the same direction. Reverse slew limit caps direction reversals.",
            "Combat scale changes authority in combat mode. Precision mode is a mode layer for fine control. Combat mode is a mode layer for combat-focused behavior. Stack mode defines how mode effects combine. Conditional rule means a rule that changes a parameter when a condition is met.",
            "Response stack means the ordered path from raw input through conditioning, shaping, limits, filtering, modes, rule injections, and final output. Output verification means a future phase has actually proven vJoy or virtual output writes; detection alone is not verification.",
        ),
    ),
    HelpArticle(
        title="Saving and Importing",
        category="Workflow",
        summary="Understand drafts, dirty state, saving, reverting, importing, and Helm changes.",
        keywords=("save", "import", "dirty", "unsaved", "revert", "helm"),
        related_topics=("Profiles", "Helm", "Runtime Setup / vJoy Setup"),
        paragraphs=(
            "The app works with a current workspace draft. Edits mark the draft as a dirty/unsaved state. Save Workspace writes the draft to `hotas_bridge_config_v3.json`; Revert restores the last saved or imported state.",
            "Import Profile brings profile data into the workspace flow when supported by the active page. Helm changes remain in memory until saved. Applying a Helm batch changes only the current draft and can be reverted through Revert Last Helm Changes before saving.",
            "command requests do not save the workspace. runtime telemetry does not modify workspace settings. Bridge command acknowledgements report command status only; they are not persistence actions.",
        ),
    ),
)


AUXILIARY_ARTICLES = (
    HelpArticle(
        title="Packaging / Installer Readiness",
        category="Getting Started",
        summary="Run from source today and understand the Phase 18 packaging and installer handoff.",
        keywords=("packaging", "installer", "source", "phase 18", "pyinstaller", "icon", "appdata"),
        related_topics=("Quick Start", "Runtime Indicators", "Performance / Diagnostics"),
        paragraphs=(
            "Phase 17C is a report-only final product QA and packaging readiness pass. Phase 18 is Packaging, Installer, Icons, and User Data Locations. The installer is not implemented in Phase 17C, and no packaging command or build script is added by this phase.",
            "Phase 18A adds packaging foundation only: packaging folder notes, a dry-run capable build script skeleton, a PyInstaller one-folder build plan, Inno Setup handoff notes, and LocalAppData user data path helpers. Phase 18A does not create an installer, does not launch driver installers, and does not change runtime truth.",
            "Phase 18B adds the first real PyInstaller one-folder build path. The expected packaged executable is `packaging/dist/HelmForge/HelmForge.exe`, and the expected packaged smoke command is `packaging/dist/HelmForge/HelmForge.exe --smoke-exit-ms 250`. Phase 18B does not create an installer, shortcuts, uninstall entry, service, tray manager, or Bridge lifecycle behavior.",
            "Phase 18C adds `packaging/inno/helmforge.iss` for the Phase 18B one-folder output. The script creates a Start Menu shortcut, offers an optional Desktop shortcut, offers optional launch after install, and adds uninstall metadata while preserving user data under LocalAppData.",
            "Run HelmForge from source with `python -m v3_app.main` after installing the editable project with `python -m pip install -e .`. The Bridge can still be launched manually from source with `python -m bridge_app.main --run-for-ms 250` when you want telemetry, but the UI does not start, stop, restart, spawn, install, or manage it.",
            "Phase 18D completes final packaging QA and Phase 19 readiness. `assets/app_icon.ico` is missing, so icon conversion remains deferred. Inno Setup compilation needs `ISCC.exe`; when it is missing, installer compile is skipped honestly. The installer does not install drivers, does not install virtual-output software, does not manage Bridge lifecycle, and keeps user data separate from app binaries.",
            "Phase 18 is now complete. Phase 19: Final Integration Kraken / Full Acceptance Sweep should validate app shell, all pages, runtime truth, Full Live Runtime Ready gate behavior, packaging, and installer behavior if available.",
        ),
    ),
    HelpArticle(
        title="Flight Recorder",
        category="Analysis",
        summary="Understand recorder settings, simulated exports, and metadata-only preview truth.",
        keywords=("flight recorder", "clip", "metadata", "simulated export", "hotkey"),
        related_topics=("Live Overlay", "Runtime Indicators", "Graphs and Previews"),
        paragraphs=(
            "Flight Recorder is currently a recorder shell with settings, shared axis overlay colors, a recording library, and a metadata-only clip preview. Simulated exports and simulated artifact manifests are clearly labeled as non-video metadata.",
            "Post-RC 3A adds a real backend design seam and a guarded capture backend capability model. The seam can report Missing, Simulated, Candidate unavailable, or Candidate available, but real capture is still not fully active unless a backend explicitly reports real capture support.",
            "Post-RC 3C adds a manually triggered one-frame proof surface. It is a diagnostic still-frame proof step only: no real video recording yet, no encoding yet, no hindsight frame buffer yet, no global recorder hotkey yet, and no game injection or graphics hooks.",
            "Post-RC 3D adds an explicit-start hindsight frame buffer and intermediate metadata artifact. Buffered frame entries are still metadata/reference proof, not encoded video, not playable preview, and not runtime readiness.",
            "The rule is simple: simulated artifacts are not real recordings. They are metadata-only artifacts or simulated export bundles; they do not contain desktop frames, playable clips, output verification, or Full Live Runtime Ready proof.",
            "The recorder does not inject into games and does not use graphics hooks. It does not add admin-level capture, hardware polling, vJoy writes, Bridge lifecycle management, cloud AI behavior, or auto-save.",
            "For now, video encoding and hindsight video buffering remain later phases. Record Now and Save Last Clip stay unavailable for real video until a verified capture backend and video buffer exist.",
            "No desktop frames are captured, no video encoding is performed, no playable clip export is produced, no recorder global hotkey is registered, and video hindsight buffering remains unavailable until later recorder phases implement and verify those behaviors.",
            "Recorder status chips are status labels, not action controls. Recording library rows and preview metadata help inspect simulated artifacts without claiming real capture or output/runtime readiness.",
        ),
    ),
    HelpArticle(
        title="Live Overlay",
        category="Analysis",
        summary="Use the app-owned detached overlay without mistaking it for game injection or capture.",
        keywords=("live overlay", "overlay", "hotkey", "click-through", "detached"),
        related_topics=("Live Monitor", "Flight Recorder", "Runtime Indicators"),
        paragraphs=(
            "Live Overlay is an app-owned detached Qt overlay window that can render simulation or telemetry-backed traces already available to the UI. It does not inject into games, hook graphics APIs, capture the screen, or prove output writes.",
            "Hotkey status, click-through support, always-on-top behavior, and active/inactive state are truth-labeled. A visible overlay means the overlay window is visible; it does not mean physical input, vJoy output, or Full Live Runtime Ready have been proven.",
            "The configuration dialog edits placement, appearance, behavior, data, and axis display settings. Applying overlay configuration does not start the Bridge, write vJoy, verify output, register a global hotkey, or save the workspace automatically.",
        ),
    ),
    HelpArticle(
        title="Live Monitor",
        category="Core Pages",
        summary="Inspect simulation, Bridge telemetry, runtime frame, physical input sample, and output-intent truth.",
        keywords=("live monitor", "runtime_frame", "telemetry", "input source", "output intent"),
        related_topics=("Runtime Indicators", "Runtime Setup / vJoy Setup", "Mapping"),
        paragraphs=(
            "Live Monitor can display runtime_frame input source, pipeline status, output intent readiness, output loop state, and last output write status when fresh Bridge telemetry includes the compact Phase 16B runtime_frame section.",
            "Phase 16C adds input proof, pipeline proof, output proof, runtime candidate, blocked reason, and proof summary. If output loop is disabled, Live Monitor labels final values as intent only. If physical input is stale or missing, the frame remains blocked or falls back safely instead of claiming live readiness.",
            "Phase 16D adds ready state, telemetry proof, safety proof, fake/real path, and the Full Live Runtime Ready gate to Live Monitor context. stale telemetry blocks readiness, fake/test paths stay labeled test-only, and a blocked reason is shown instead of a generic ready claim.",
            "runtime_frame values are truth-labeled telemetry summaries. A simulation-backed runtime_frame proves the simulation pipeline and output intent path, not live hardware output. output intent is not necessarily an output write, and output loop state must be read separately from output intent readiness.",
            "If runtime_frame is missing, stale, or malformed, Live Monitor keeps its existing simulation or Bridge telemetry fallback behavior. It must not claim output_verified or Full Live Runtime Ready unless telemetry explicitly proves those fields under the documented runtime rules.",
        ),
    ),
)


def _structured_article(
    title: str,
    *,
    topic_category: str,
    category: str,
    summary: str,
    sections: tuple[tuple[str, tuple[str, ...]], ...],
    keywords: tuple[str, ...] = (),
    related_topics: tuple[str, ...] = (),
    open_page_id: str | None = None,
    parameter_ids: tuple[str, ...] = (),
    importance: int = 50,
) -> HelpArticle:
    article_sections = tuple(HelpArticleSection(heading=heading, body=body) for heading, body in sections)
    paragraphs = tuple(sentence for _heading, body in sections for sentence in body)
    return HelpArticle(
        title=title,
        category=category,
        summary=summary,
        paragraphs=paragraphs,
        keywords=keywords,
        related_topics=related_topics,
        sections=article_sections,
        topic_category=topic_category,
        open_page_id=open_page_id,
        parameter_ids=parameter_ids,
        importance=importance,
    )


POST_RC_1D_ARTICLES = (
    _structured_article(
        "HelmForge overview",
        topic_category="Getting Started",
        category="Getting Started",
        summary="A concise orientation to the local HOTAS tuning workspace.",
        keywords=("overview", "manual", "workspace", "simulation"),
        related_topics=("Quick Start", "Simulation mode", "Runtime truth model"),
        open_page_id="mapping",
        importance=100,
        sections=(
            ("What this is", ("HelmForge is a local HOTAS tuning workspace for mapping, tuning, diagnostics, and conservative runtime truth.",)),
            ("What it does", ("It lets you edit a workspace draft, inspect simulated or telemetry-backed response behavior, and save intentionally when the draft is ready.",)),
            ("When to use it", ("Start here when you need the mental model before changing Mapping, Tuning, Rules, Live Monitor, Recorder, or Diagnostics pages.",)),
            ("Runtime truth notes", ("Telemetry remains the truth surface. Simulation mode remains available and does not claim live hardware readiness.",)),
        ),
    ),
    _structured_article(
        "Simulation mode",
        topic_category="Getting Started",
        category="Getting Started",
        summary="Use HelmForge safely without HOTAS hardware or verified output.",
        keywords=("simulation", "fallback", "missing device"),
        related_topics=("Runtime truth model", "Quick Start"),
        importance=96,
        sections=(
            ("What this is", ("Simulation mode is the safe default path when hardware, telemetry, or output verification is unavailable.",)),
            ("What it does", ("It keeps Mapping, tuning previews, response stack inspection, Helm recommendations, and docs usable without writing output.",)),
            ("Common mistakes", ("Do not treat simulated graphs, output intent, or packaged app smoke as runtime readiness.",)),
            ("Runtime truth notes", ("vJoy detected is not output verification, physical input alone is not full readiness, and fake/test paths are not real readiness.",)),
        ),
    ),
    _structured_article(
        "Runtime truth model",
        topic_category="Runtime Truth",
        category="Analysis",
        summary="The shared vocabulary for telemetry, intent, verification, and readiness.",
        keywords=("runtime truth", "telemetry", "intent", "verification"),
        related_topics=("Runtime Indicators", "Full Live Runtime Ready", "Bridge telemetry"),
        importance=98,
        sections=(
            ("What this is", ("Runtime truth is the typed evidence model shown across Help, Mapping, Live Monitor, and Perf / Diagnostics.",)),
            ("What it does", ("It separates process hints, command requests, telemetry freshness, physical input proof, output intent, output write proof, and readiness.",)),
            ("Common mistakes", ("Command files are requests, not success proof. Output intent is not output write proof. vJoy detected is not output verification.",)),
            ("Runtime truth notes", ("Full Live Runtime Ready gates remain unchanged and require the Phase 16 proof chain.",)),
        ),
    ),
    _structured_article(
        "Full Live Runtime Ready",
        topic_category="Runtime Truth",
        category="Analysis",
        summary="The final readiness gate and why it remains conservative.",
        keywords=("full live runtime ready", "gate", "proof", "readiness"),
        related_topics=("Runtime Indicators", "vJoy/output verification", "Bridge telemetry"),
        importance=99,
        sections=(
            ("What this is", ("Full Live Runtime Ready is the final Phase 16 readiness gate, not a UI styling state or packaging state.",)),
            ("What it does", ("It requires fresh physical input, successful pipeline processing, guarded real output verification, explicit output-loop state, fresh telemetry, and no safety stop.",)),
            ("Common mistakes", ("Do not infer it from vJoy detection, HOTAS detection, output intent generation, fake verification, fake output loops, stale telemetry, or UI process presence.",)),
            ("Runtime truth notes", ("Packaged smoke is not runtime readiness. Real hardware proof is not claimed unless the gate evidence exists.",)),
        ),
    ),
    _structured_article(
        "vJoy/output verification",
        topic_category="Runtime Truth",
        category="Analysis",
        summary="How virtual output proof differs from detection and intent.",
        keywords=("vjoy", "output verification", "output intent", "write proof"),
        related_topics=("Full Live Runtime Ready", "Runtime Setup / vJoy Setup"),
        importance=95,
        sections=(
            ("What this is", ("Output verification is guarded proof that output writes succeeded through the virtual output backend.",)),
            ("What it does", ("It keeps dependency detection, selected output device, final output intent, fake output tests, and real write proof separate.",)),
            ("Common mistakes", ("vJoy detected does not equal output verified. Output intent is not output write proof.",)),
            ("Runtime truth notes", ("Fake/mock verification is not real output verification and cannot make Full Live Runtime Ready true.",)),
        ),
    ),
    _structured_article(
        "Bridge telemetry",
        topic_category="Runtime Truth",
        category="Analysis",
        summary="How Bridge-provided data becomes the truth surface.",
        keywords=("bridge", "telemetry", "runtime_frame", "stale", "invalid"),
        related_topics=("Runtime Indicators", "Performance / Diagnostics"),
        importance=94,
        sections=(
            ("What this is", ("Bridge telemetry is the runtime truth surface when fresh, parseable, and consistent.",)),
            ("What it does", ("It can carry lifecycle, runtime_frame, output verification, physical input, output loop, blocked reason, and proof summary fields.",)),
            ("Common mistakes", ("Process presence is a hint only. Stale, missing, or invalid telemetry cannot prove readiness.",)),
            ("Runtime truth notes", ("The UI does not start, stop, restart, spawn, install, or manage the Bridge.",)),
        ),
    ),
    _structured_article(
        "HOTAS diagram",
        topic_category="Mapping",
        category="Core Pages",
        summary="Read the visual mapping diagram without mistaking it for live hardware control.",
        keywords=("hotas diagram", "mapping", "visual", "markers"),
        related_topics=("Mapping", "Mapping Route Inspector"),
        open_page_id="mapping",
        parameter_ids=("mapping.raw_axis", "mapping.hotas_button", "mapping.hotas_hat"),
        importance=92,
        sections=(
            ("What this is", ("The HOTAS diagram is a visual workspace map of configured axes, buttons, and hats.",)),
            ("What it does", ("It highlights mapped, unmapped, selected, and warning states while reusing Mapping route metadata.",)),
            ("When to use it", ("Use it to find which physical control corresponds to a route before opening the inspector/editor.",)),
            ("Runtime truth notes", ("The diagram does not poll hardware and does not write vJoy. It reflects workspace/config routing plus available read-only telemetry labels.",)),
        ),
    ),
    _structured_article(
        "Mapping Route Inspector",
        topic_category="Mapping",
        category="Core Pages",
        summary="Inspect selected diagram routes and conflict previews.",
        keywords=("route inspector", "mapping", "conflict", "selected"),
        related_topics=("Mapping edit workflow", "HOTAS diagram"),
        open_page_id="mapping",
        importance=91,
        sections=(
            ("What this is", ("The Route Inspector explains the selected route and whether it is being inspected or edited as a workspace draft.",)),
            ("What it does", ("It shows route type, source, output intent, warnings, and config conflict previews before draft changes are applied.",)),
            ("Common mistakes", ("A conflict preview is not hardware failure. It is a workspace/config warning.",)),
            ("Runtime truth notes", ("Output intent shown here remains intent only and is not output write proof.",)),
        ),
    ),
    _structured_article(
        "Mapping edit workflow",
        topic_category="Mapping",
        category="Workflow",
        summary="Safely edit diagram-selected Mapping routes as workspace drafts.",
        keywords=("mapping edit workflow", "apply to draft", "save workspace", "route editor"),
        related_topics=("Mapping", "Mapping Route Inspector", "Saving and Importing"),
        open_page_id="mapping",
        parameter_ids=("mapping.raw_axis", "mapping.logical_output", "mapping.runtime_output_axis", "mapping.invert_axis"),
        importance=97,
        sections=(
            ("What this is", ("Post-RC 2C promotes the Mapping diagram from inspection-only selection into a safe workspace draft editor.",)),
            ("What it does", ("Click or focus a routed marker, review it in Route Inspector, choose Change Mapping, adjust supported route fields, preview conflicts, then Apply to Draft or Cancel.",)),
            ("When to use it", ("Use it when the selected axis, button, or hat should change its workspace/config route without touching runtime authority.",)),
            ("Key parameters", ("Raw Axis, Logical Output, Output Intent Axis, Invert Axis, HOTAS Button, Output Button, HOTAS Hat, Output POV, and Hat Direction Button are metadata-backed where supported.",)),
            ("Runtime truth notes", ("Mapping edits are workspace/config draft only. Save Workspace is required to persist. Output intent is not vJoy write proof.",)),
            ("Related topics", ("See HOTAS diagram, Mapping Route Inspector, Axis routing, Button routing, and Hat routing.",)),
        ),
    ),
    _structured_article(
        "Axis routing",
        topic_category="Mapping",
        category="Core Pages",
        summary="Route raw axes to logical and output-intent axes.",
        keywords=("axis routing", "raw axis", "logical output", "invert"),
        related_topics=("Mapping edit workflow", "Base Tuning"),
        open_page_id="mapping",
        parameter_ids=("mapping.raw_axis", "mapping.logical_output", "mapping.runtime_output_axis", "mapping.invert_axis"),
        sections=(
            ("What this is", ("Axis routing connects a physical/raw axis channel to a logical workspace output and output-intent axis.",)),
            ("Suggested ranges", ("Dropdowns list only supported route options from the current Mapping page.",)),
            ("Runtime truth notes", ("Changing an axis route changes the draft workspace, not live vJoy output.",)),
        ),
    ),
    _structured_article(
        "Button routing",
        topic_category="Mapping",
        category="Core Pages",
        summary="Route physical buttons to output button intent.",
        keywords=("button routing", "hotas button", "output button"),
        related_topics=("Mapping edit workflow"),
        open_page_id="mapping",
        parameter_ids=("mapping.hotas_button", "mapping.output_button"),
        sections=(
            ("What this is", ("Button routing maps a physical button label to an output button intent.",)),
            ("Common mistakes", ("A pressed-state display is telemetry/simulation context, not proof that output was written.",)),
            ("Runtime truth notes", ("Save Workspace persists the draft route; runtime proof remains separate.",)),
        ),
    ),
    _structured_article(
        "Hat routing",
        topic_category="Mapping",
        category="Core Pages",
        summary="Route physical hat controls to POV and optional button intent.",
        keywords=("hat routing", "pov", "direction button"),
        related_topics=("Mapping edit workflow"),
        open_page_id="mapping",
        parameter_ids=("mapping.hotas_hat", "mapping.output_pov", "mapping.hat_direction_button"),
        sections=(
            ("What this is", ("Hat routing maps the physical hat to output POV intent and optional direction button intent fields.",)),
            ("When to use it", ("Use it when the workspace needs POV-style routing or directional button fallbacks.",)),
            ("Runtime truth notes", ("Hat routing is still workspace/config draft behavior, not output verification.",)),
        ),
    ),
    _structured_article(
        "Curve modes",
        topic_category="Tuning",
        category="Reference",
        summary="Understand the currently supported curve mode options.",
        keywords=("curve modes", "curve mode", "s curve"),
        related_topics=("Base Tuning", "Parameter Reference"),
        open_page_id="base_tuning",
        parameter_ids=("base.curve_mode", "base.curve_strength"),
        sections=(
            ("What this is", ("Curve Mode chooses the shape family used before strength is applied.",)),
            ("Suggested ranges", ("Current UI options are intentionally limited to supported values from the metadata registry.",)),
            ("Runtime truth notes", ("Changing curve values changes workspace math only until saved and later consumed by the pipeline.",)),
        ),
    ),
    _structured_article(
        "Deadzone / anti-deadzone",
        topic_category="Tuning",
        category="Reference",
        summary="Balance center noise rejection with initial response.",
        keywords=("deadzone", "anti-deadzone", "center"),
        related_topics=("Base Tuning", "Parameter Reference"),
        open_page_id="base_tuning",
        parameter_ids=("base.deadzone", "base.anti_deadzone"),
        sections=(
            ("What this is", ("Deadzone ignores small input near center; anti-deadzone adds a controlled initial output after leaving center.",)),
            ("Examples", ("Low deadzone responds to tiny motion. High deadzone calms drift but can feel unresponsive.",)),
            ("Common mistakes", ("Do not use high anti-deadzone to compensate for a route problem; it can make fine control lurch.",)),
        ),
    ),
    _structured_article(
        "Hysteresis",
        topic_category="Tuning",
        category="Reference",
        summary="Reduce chatter from small reversals.",
        keywords=("hysteresis", "jitter", "center chatter"),
        related_topics=("Base Tuning", "Filtering"),
        open_page_id="base_tuning",
        parameter_ids=("base.hysteresis",),
        sections=(
            ("What this is", ("Hysteresis adds a small hold band so tiny direction changes do not constantly flip state.",)),
            ("Common mistakes", ("Too much hysteresis can hide intentional small inputs.",)),
        ),
    ),
    _structured_article(
        "Output scale / max output",
        topic_category="Tuning",
        category="Reference",
        summary="Limit or expand workspace output authority.",
        keywords=("output scale", "max output", "authority"),
        related_topics=("Base Tuning", "Runtime truth model"),
        open_page_id="base_tuning",
        parameter_ids=("base.output_scale", "base.max_output", "base.precision_scale"),
        sections=(
            ("What this is", ("Output scale multiplies processed output; Max Output clamps final authority.",)),
            ("Runtime truth notes", ("Output scale changes output intent math and does not prove an output write.",)),
        ),
    ),
    _structured_article(
        "Slew limits",
        topic_category="Filtering",
        category="Reference",
        summary="Control same-direction and reverse-direction rate changes.",
        keywords=("slew limits", "same slew", "reverse slew"),
        related_topics=("Filtering", "Combat Profile"),
        open_page_id="filtering",
        parameter_ids=("filtering.same_slew_limit", "filtering.reverse_slew_limit"),
        sections=(
            ("What this is", ("Slew limits cap how quickly the processed signal can change in the same or reverse direction.",)),
            ("Examples", ("Higher limits feel more immediate. Lower limits can calm abrupt changes but may feel delayed.",)),
        ),
    ),
    _structured_article(
        "Precision mode",
        topic_category="Modes",
        category="Core Pages",
        summary="Use precision controls for fine movement layers.",
        keywords=("precision mode", "precision hold buttons"),
        related_topics=("Modes", "Stack mode"),
        open_page_id="modes",
        parameter_ids=("modes.precision_hold_buttons",),
        sections=(
            ("What this is", ("Precision mode is a workspace mode layer for fine control.",)),
            ("Runtime truth notes", ("Mode buttons are configuration until telemetry proves input and the runtime path.",)),
        ),
    ),
    _structured_article(
        "Combat mode",
        topic_category="Modes",
        category="Core Pages",
        summary="Use combat gates with combat tuning parameters.",
        keywords=("combat mode", "combat trigger", "zoom aim"),
        related_topics=("Combat Profile", "Modes"),
        open_page_id="modes",
        parameter_ids=("modes.combat_trigger_buttons", "modes.combat_zoom_aim_buttons", "modes.combat_extra_buttons"),
        sections=(
            ("What this is", ("Combat mode gates combat-focused tuning layers.",)),
            ("Runtime truth notes", ("Configured buttons do not prove physical input is fresh or output is verified.",)),
        ),
    ),
    _structured_article(
        "Stack mode",
        topic_category="Modes",
        category="Core Pages",
        summary="Understand how mode effects combine.",
        keywords=("stack mode", "multiply"),
        related_topics=("Modes", "Combat Profile"),
        open_page_id="modes",
        parameter_ids=("modes.stack_mode",),
        sections=(
            ("What this is", ("Stack Mode controls how mode effects combine.",)),
            ("Common mistakes", ("Multiply stacking can compound reductions more than expected.",)),
        ),
    ),
    _structured_article(
        "Rule stages",
        topic_category="Conditional Rules",
        category="Advanced Pages",
        summary="Where conditional rules inject into the response stack.",
        keywords=("rule stages", "injects at", "stage"),
        related_topics=("Conditional Rules", "Effective Response Stack"),
        open_page_id="conditional_rules",
        parameter_ids=("rules.injects_at", "rules.stage", "rules.reference_stage"),
        sections=(
            ("What this is", ("Rule stages describe where the rule reads or injects within the response stack.",)),
            ("Runtime truth notes", ("Rule injection metadata is workspace/pipeline evidence, not hardware output proof.",)),
        ),
    ),
    _structured_article(
        "Comparators",
        topic_category="Conditional Rules",
        category="Advanced Pages",
        summary="How rule conditions compare measured values.",
        keywords=("comparators", "threshold", "between", "greater than"),
        related_topics=("Conditional Rules", "Rule stages"),
        open_page_id="conditional_rules",
        parameter_ids=("rules.comparator", "rules.threshold", "rules.threshold_high"),
        sections=(
            ("What this is", ("Comparators decide whether a measured value crosses a threshold or range.",)),
            ("Common mistakes", ("Invalid thresholds block the rule instead of crashing the pipeline.",)),
        ),
    ),
    _structured_article(
        "Recorder review/export diagnostics",
        topic_category="Flight Recorder",
        category="Analysis",
        summary="Review simulated recorder sessions and export diagnostics without claiming video.",
        keywords=("recorder review export diagnostics", "json", "csv", "metadata"),
        related_topics=("Flight Recorder", "Real capture limitations"),
        open_page_id="flight_recorder",
        importance=88,
        sections=(
            ("What this is", ("Post-RC 3B adds recorder review and export diagnostics for simulated or metadata-only recorder artifacts.",)),
            ("What it does", ("It can summarize sessions and export local JSON or CSV diagnostic data where supported.",)),
            ("Runtime truth notes", ("Exports are diagnostics, not real video recordings, not previewable clips, and not runtime readiness proof.",)),
        ),
    ),
    _structured_article(
        "One-frame capture proof",
        topic_category="Flight Recorder",
        category="Analysis",
        summary="Understand the manual still-frame proof added in Post-RC 3C.",
        keywords=("one-frame capture proof", "still frame", "capture proof"),
        related_topics=("Flight Recorder", "Real capture limitations"),
        open_page_id="flight_recorder",
        importance=89,
        sections=(
            ("What this is", ("Post-RC 3C adds a manually triggered one-frame capture proof surface.",)),
            ("What it does", ("It can request one still-frame proof from a capable backend and records typed proof metadata when available.",)),
            ("Common mistakes", ("one-frame capture proof is not video recording. It is not a continuous capture loop, not a playable preview, and not an encoded export.",)),
            ("Runtime truth notes", ("No continuous recorder capture yet. No video encoding/export/preview yet. Capture proof is not runtime readiness.",)),
        ),
    ),
    _structured_article(
        "Real capture limitations",
        topic_category="Flight Recorder",
        category="Analysis",
        summary="Recorder capture boundaries after the 3C proof phase.",
        keywords=("real capture limitations", "video encoding", "buffering", "preview"),
        related_topics=("One-frame capture proof", "Recorder review/export diagnostics"),
        open_page_id="flight_recorder",
        sections=(
            ("What this is", ("The recorder has a capture seam and a one-frame proof, but no continuous capture product yet.",)),
            ("What it does", ("It truthfully labels missing, simulated, candidate-unavailable, candidate-available, and one-frame proof states.",)),
            ("Runtime truth notes", ("No continuous recorder capture yet. No video encoding/export/preview yet. No game injection or graphics API hooking was added.",)),
        ),
    ),
    _structured_article(
        "Parameter Reference",
        topic_category="Parameter Reference",
        category="Reference",
        summary="Searchable parameter metadata from the shared registry.",
        keywords=("parameter reference", "metadata", "range", "default", "scope"),
        related_topics=("Base Tuning", "Mapping", "Flight Recorder"),
        parameter_ids=tuple(metadata.parameter_id for metadata in parameter_reference_entries()),
        importance=93,
        sections=(
            ("What this is", ("Parameter Reference is generated from the shared Post-RC metadata registry.",)),
            ("What it does", ("Each block lists display name, page/category, support scope, value type, ranges or options, default value, examples, warnings, and related help topic when available.",)),
            ("Runtime truth notes", ("Parameter help explains configuration. It does not activate runtime, poll hardware, write vJoy, or weaken readiness gates.",)),
        ),
    ),
    _structured_article(
        "Troubleshooting",
        topic_category="Troubleshooting",
        category="Reference",
        summary="Read common blocked states without turning them into false readiness.",
        keywords=("troubleshooting", "blocked", "stale", "missing", "invalid"),
        related_topics=("Runtime truth model", "Performance / Diagnostics"),
        open_page_id="perf_diagnostics",
        importance=86,
        sections=(
            ("What this is", ("Troubleshooting explains common blocked states and where to inspect the truth fields.",)),
            ("Common mistakes", ("Do not treat process presence, command acknowledgement, vJoy detection, or one-frame capture proof as readiness.",)),
            ("Runtime truth notes", ("Use Perf / Diagnostics for telemetry freshness, blocked reason, proof summary, and Full Live Runtime Ready gate details.",)),
        ),
    ),
)
