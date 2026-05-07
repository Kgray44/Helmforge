from __future__ import annotations

from dataclasses import dataclass


HELP_CATEGORY_ORDER = (
    "Advanced Pages",
    "Analysis",
    "Core Pages",
    "Diagnostics",
    "Getting Started",
    "Reference",
    "Workflow",
)


@dataclass(frozen=True)
class HelpArticle:
    title: str
    category: str
    summary: str
    paragraphs: tuple[str, ...]
    keywords: tuple[str, ...] = ()
    related_topics: tuple[str, ...] = ()

    @property
    def body(self) -> str:
        return "\n\n".join(self.paragraphs)

    @property
    def search_text(self) -> str:
        return " ".join((self.title, self.category, self.summary, " ".join(self.keywords), self.body))


@dataclass(frozen=True)
class HelpSearchResult:
    article: HelpArticle
    score: int


def all_articles() -> tuple[HelpArticle, ...]:
    return ARTICLES


def articles_by_category() -> dict[str, tuple[HelpArticle, ...]]:
    grouped: dict[str, list[HelpArticle]] = {category: [] for category in HELP_CATEGORY_ORDER}
    for article in ARTICLES:
        grouped.setdefault(article.category, []).append(article)
    return {category: tuple(grouped.get(category, ())) for category in HELP_CATEGORY_ORDER}


def get_article(title: str) -> HelpArticle:
    normalized = _normalize(title)
    for article in ARTICLES:
        if _normalize(article.title) == normalized:
            return article
    raise KeyError(title)


def search_articles(query: str) -> tuple[HelpSearchResult, ...]:
    terms = tuple(term for term in _normalize(query).split() if term)
    if not terms:
        return tuple(HelpSearchResult(article=article, score=0) for article in ARTICLES)

    results: list[HelpSearchResult] = []
    for article in ARTICLES:
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
                HELP_CATEGORY_ORDER.index(result.article.category),
                result.article.title,
            ),
        )
    )


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
            "Rules appear through shared rule injection metadata at their actual stack context. If stack data is simulated or unavailable, the page and Help / Docs should say so plainly instead of implying live hardware analysis.",
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
        summary="Read local response previews without confusing them for verified live output.",
        keywords=("graphs", "preview", "raw", "final", "curve"),
        related_topics=("Effective Response Stack", "Runtime Indicators", "Base Tuning"),
        paragraphs=(
            "Graphs and previews show how the current workspace math is expected to transform input. They help compare raw input, shaped response, filtered response, and final output from the shared-core pipeline.",
            "A graph can be useful even in simulation mode, but it is not proof that a physical HOTAS is being polled or that vJoy output writes are verified. Treat graph values as workspace or telemetry evidence depending on the source label.",
            "Phase 12A adds Live Overlay core/config foundations, and Phase 12B adds an app-owned detached overlay window and renderer. Overlay traces can use simulation or runtime snapshot values already available to the UI, but they do not prove live hardware, vJoy writes, or output verification.",
            "Live Overlay is app-owned and detached. It does not inject into games, does not use graphics API hooking, and does not capture the screen. Hotkey and click-through statuses are truth-labeled; they are not claimed unless implemented and verified. Flight Recorder is a separate later phase.",
            "Phase 13A adds Flight Recorder UI/state/settings/library/preview shell only. Axis overlay colors reuse the Live Overlay color model, but real capture and encoding are deferred, hindsight video buffering is deferred, recorder hotkey registration is deferred, and the recorder shell does not add screen capture, game injection, graphics API hooking, or runtime activation.",
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
            "Output verified means actual output writes have been proven by a future verification phase. Full Live Runtime Ready means both input and output are proven. In the current Phase 11A boundary, output_verified remains false and Full Live Runtime Ready remains false.",
            "HOTAS discovery and Device discovery are read-only identity checks. Process hint is only a diagnostic hint and never becomes runtime truth. Command acknowledgement means Bridge telemetry has a matching request_id for the latest UI command request.",
            "Stale telemetry is too old to treat as fresh. Missing telemetry means the file is not present. Invalid telemetry means the JSON could not be parsed or validated. Simulation fallback keeps the UI usable when telemetry is stale, missing, or invalid.",
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
            "Base Tuning is configuration work. It does not write to vJoy and does not verify live output. Save Workspace is required to persist edits to the V3 workspace file.",
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
            "Mapping edits update the in-memory workspace draft and can be saved to `hotas_bridge_config_v3.json`. The page can show simulation or telemetry-backed values, but mapping itself does not write vJoy.",
            "If the physical HOTAS is missing, mapping can still be edited safely. Runtime truth may remain blocked_missing_device until a later hardware/runtime phase proves live input and output.",
        ),
    ),
    HelpArticle(
        title="Performance / Diagnostics",
        category="Diagnostics",
        summary="Inspect app timing, runtime truth, Bridge telemetry, and safe preflight visibility.",
        keywords=("performance", "diagnostics", "perf", "phase 11b", "timings", "preflight"),
        related_topics=("Runtime Indicators", "Runtime Setup / vJoy Setup"),
        paragraphs=(
            "Performance / Diagnostics is the diagnostics half of Phase 11. Diagnostics are observational. The page surfaces runtime truth, telemetry freshness, Bridge lifecycle, HOTAS discovery, output verification truth, workspace state, and lightweight UI timing metrics.",
            "Run Runtime Preflight is safe and does not verify output. It refreshes preflight truth but does not install drivers, launch installers, start the Bridge, poll live HOTAS input, write virtual output, verify output, or activate runtime.",
            "timing metrics are app/UI diagnostics, not live hardware proof. hidden-page skip counters show skipped expensive updates where instrumented, and unavailable counters are labeled truthfully.",
            "Copy Diagnostics creates local diagnostic text. output_verified remains false until a future verification phase proves writes. Full Live Runtime Ready remains false until future phases prove both input and output.",
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
            "Save Workspace when you want to keep the current draft. Until future live runtime phases are implemented, do not treat simulation graphs or vJoy detection as verified live output.",
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
            "physical HOTAS discovery is discovery-only until later hardware/runtime phases. A supported device discovery result does not mean live HOTAS polling exists, live input streaming exists, vJoy writes exist, or Full Live Runtime Ready has been proven.",
            "vJoy detected does not equal output verified. output_verified remains false until a future output verification phase proves writes. Full Live Runtime Ready remains false until future phases prove both input and output. Missing HOTAS means runtime truth may be blocked_missing_device.",
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
