# Morphological Analysis: ForgeViz Differentiation

**Date:** 2026-05-25
**Technique:** Morphological Analysis (Zwicky Box)

## Morphological Box

| Dimension | Option 1 | Option 2 | Option 3 | Option 4 | Option 5 |
|-----------|----------|----------|----------|----------|----------|
| **Process Context** | Dumb Container | Annotation Layer (pluggable overlay) | Embedded Process Model (carries stat model) | Process Digital Twin (live causal model) | Adversarial Context (gap between theoretical/actual) |
| **Analytical Autonomy** | Pure Renderer | Defensive Hygiene (auto-scale, misconfig flag) | Opt-In Insight Layer | Opinionated Narrator (always companion narrative) | Autonomous Investigator (spawns follow-ups by info gain) |
| **Artifact Portability** | Web-Only Widget | Static Export (SVG/PNG/PDF) | Self-Contained HTML (single file, interactive) | Adaptive Fidelity (detects context) | Physical-First (thermal printer) |
| **Spec Ergonomics** | Explicit Dataclass | Convention Shorthand (domain DSL) | Natural Language Front-End | Institutional Template Library | Example-Driven (screenshot to spec) |
| **Temporal Continuity** | Stateless Function Call | Versioned Artifact (diffable) | Streaming Entity (maintains state) | Anticipatory (pre-computes futures) | Genealogical Lineage (charts spawn children) |

**Total design space:** 3,125 combinations

## Random Combinations Evaluated

### Combo 1: Dumb Container + Pure Renderer + Self-Contained HTML + Convention Shorthand + Versioned Artifact
**Feasible:** Yes. The "Excel chart that remembers its history." Self-contained HTML files that you can `diff` against last week's. Convention shorthand makes diffs readable. Less intelligence creates more utility — the versioning makes the human smart.

### Combo 2: Annotation Layer + Pure Renderer + Physical-First + Explicit Dataclass + Genealogical Lineage
**Feasible:** No (thermal printout can't spawn children). **Fix:** Replace lineage with stateless = shop-floor label printer with annotation callouts. The failed combo reveals: lineage belongs in the dispatch system, not the artifact. Separates concerns correctly when fixed.

### Combo 3: Digital Twin + Pure Renderer + Web-Only + Explicit Dataclass + Versioned Artifact
**Feasible:** With mod (twin contradicts pure renderer). **Fix:** Bump to defensive hygiene. Intelligence in data layer, not rendering layer. Versioned artifact lets you diff model predictions over time — detect analytical drift, not just process drift.

### Combo 4: Annotation Layer + Autonomous Investigator + Physical-First + Explicit Dataclass + Genealogical Lineage
**Feasible:** No (triple collision). Forces the question: what's the relationship between investigator (prospective: what to look at) and lineage (record: what was spawned)? They're not the same thing. Recommendation vs. provenance.

### Combo 5: Annotation Layer + Autonomous Investigator + Adaptive Fidelity + Convention Shorthand + Anticipatory
**Feasible:** With mod (constrain anticipatory to top-ranked follow-up only). Adaptive fidelity is the sleeper — investigation doesn't change, presentation adapts. Reveals that **autonomous analysis needs a spec language optimized for machine authorship**, not human authorship.

### Combo 6: Adversarial Context + Opt-In Insight + Web-Only + Convention Shorthand + Anticipatory
**Feasible:** Yes. The "Socratic chart" — shows the gap between theoretical and actual, knows where it's heading, but waits for you to ask. Pedagogically powerful. Quality engineer forms hypothesis, clicks "why?", system reveals what it already computed. Makes the user think before revealing.

### Combo 7: Embedded Process Model + Opt-In Insight + Static Export + Convention Shorthand + Streaming Entity
**Feasible:** With mod (static export → adaptive fidelity). The "living control chart" — `xbar(stream, subgroup=5)` as convention shorthand that carries its own model, streams data, degrades to PDF for email. Eliminates the "export → Minitab → chart → paste in report" workflow.

### Combo 8: Dumb Container + Pure Renderer + Adaptive Fidelity + Explicit Dataclass + Streaming Entity
**Feasible:** Yes. The baseline architecture. Validates ForgeViz's current design as the correct degenerate case. Every other combination is this one plus layers.

## Three Most Promising

### 1. The Socratic Chart (Combo 6)
**Adversarial Context + Opt-In Insight + Convention Shorthand + Anticipatory**

The chart explicitly renders the gap between theoretical and actual performance. The system knows where the gap is heading (anticipatory) but waits for you to ask (opt-in). Convention shorthand keeps specs simple.

**Why it's differentiated:** Cpk IS a gap metric. Yield IS actual-vs-theoretical. Manufacturing data is inherently adversarial (reality vs. spec). No competitor frames charts this way. Minitab dumps analysis. Plotly shows whatever you tell it. This makes ForgeViz a thinking tool — it knows the answer but makes you ask the question.

**Implementation path:** New `gap_overlay()` function + `anticipatory` field on ChartSpec that stores pre-computed projections. Opt-in insight already exists as the `enrich()` function in analytics.

### 2. The Living Control Chart (Combo 7 modified)
**Embedded Process Model + Opt-In Insight + Adaptive Fidelity + Convention Shorthand + Streaming Entity**

`xbar("diameter", subgroup=5)` → live streaming control chart with embedded SPC model that degrades to PDF for reports. The chart IS the monitoring system.

**Why it's differentiated:** Kills the Minitab workflow entirely. The chart carries its own model (not just data), streams live data, and adapts output format to context. No competitor offers a chart that is simultaneously a monitoring tool, a statistical engine, and a portable document.

**Implementation path:** Streaming is the new primitive — `ChartSpec.append(data)` that updates running statistics. Embedded model already exists via forge packages. Convention shorthand is a thin DSL layer over existing chart builders.

### 3. The Diffable Chart (Combo 1)
**Self-Contained HTML + Convention Shorthand + Versioned Artifact**

Self-contained HTML files with version history. `git diff` two chart versions and see what changed — data and configuration both tracked.

**Why it's differentiated:** Zero competitors offer diffable chart history. Git for charts. A quality manager sees not just today's chart but how it evolved over months. Audit gold. SOC 2 artifact.

**Implementation path:** `to_html()` renderer + `ChartSpec.version()` method that returns a content hash. Convention shorthand makes diffs readable. Could ship in days.

## Unexpected Interactions

### Analytical Autonomy x Temporal Continuity = Governance Problem
Autonomous Investigator + Genealogical Lineage creates a feedback loop — charts spawning charts spawning charts. Needs a budget: max lineage depth, max spawned investigations per parent.

### Process Context Constrains Spec Ergonomics
Convention shorthand works for simple charts but breaks for digital twins. Suggests ForgeViz needs two spec interfaces: shorthand for simple, full dataclass for model-carrying.

### Artifact Portability is the Constraining Dimension
Physical-first kills streaming/genealogical/anticipatory. Static export conflicts with streaming. Decide portability first — it narrows temporal options. ForgeViz's current static-export strength actually limits temporal evolution.

### Adversarial Context is Uniquely Paired with Opt-In Insight
The gap is visible. The explanation is available on demand. No other process context option creates this "I can see it, now let me ask" dynamic. This pairing wasn't obvious from the dimensions alone.
