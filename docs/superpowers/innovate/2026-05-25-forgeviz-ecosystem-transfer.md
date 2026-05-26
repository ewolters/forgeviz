# Cross-Domain Transfer: ForgeViz vs Ecosystem

**Date:** 2026-05-25
**Technique:** Analogical Transfer
**Domains:** Cuisine, Cartography, Theater, Military Intelligence

## Domain Solutions

### Cuisine — The Brigade de Cuisine
Reframe: You run a 104-item menu from a zero-dependency kitchen. Competitors are hotel banquet operations.

Five genuine gaps identified:
1. **Garde Manger** — fast-path for the 12 most common presentations
2. **Family-style service** — composed multi-chart from one dataset
3. **Mother sauce lineage** — trace any chart back to source (tree, not web)
4. **Maître d'** — wayfinding for complex presentations ("you are here")
5. **Takeaway** — charts that survive email/PDF without losing composition

Rejected: tableside theatrics (3D/animation), menu inflation, collaborative editing

Principle: *"Escoffier won by organizing the stations, not by cooking more dishes."*

### Cartography — The Atlas Assessment
Reframe: A 104-projection atlas serving three readers with different wayfinding needs.

Five genuine gaps:
1. **Marginalia** — annotation layer where users inscribe interpretation
2. **Systematic plate series** — small multiples at identical scale
3. **Hypsometric tinting** — threshold shading (green/yellow/red classification)
4. **Multi-scale generalization** — overview → detail drill-through
5. **Composite plates** — two information layers on one chart

Rejected: 3D perspective, animation, projection count inflation, collaborative editing

Principle: *"Fitness of projection to purpose beats universality of projection library."*

### Theater — The Repertory Company
Reframe: A 104-actor ensemble touring three venues (boardroom, audit chamber, shop floor).

**Reframed the problem:** Not "what charts are missing" but "there is no directing layer."

Five gaps:
1. **Audience contract** — boardroom (90s verdict), audit (evidence), floor (5s signal)
2. **Three production concepts** — Executive Curtain Call / Audit Dossier / Shop Floor Andon
3. **Dramaturgical layer** — recommendation by audience, not just data shape
4. **Touring set as identity** — self-contained HTML IS the product model, not a feature
5. **Venue parameter** — same chart, different blocking per audience

Rejected: grand opera (becoming the bloated competitors)

Principle: *"Same ensemble, directed three ways, is more valuable than three separate companies — but only if the directing layer exists."*

### Military Intelligence — The S-2 Assessment
Reframe: An organic intelligence cell producing products for three echelons.

Priority 1 (Critical):
1. **Collaborative annotation** — consumers add meaning (the annotation IS the intelligence)
2. **Tiered dissemination** — one dataset → three products by role
3. **Narrative assessment** — structured judgment with stated confidence

Priority 2 (Significant):
4. **Collection management** — blind spot detection (what data SHOULD exist but doesn't)
5. **PIR alerting** — threshold-based interrupts, not polling

Rejected: drag-and-drop builders (untrained noise), AI auto-insights (unsigned intelligence), connector ecosystems (vendor lock-in), social features, 500+ chart types

Principle: *"The right product, to the right consumer, at the right time, in the right format, to support a specific decision."*

## Synthesis

### Novel Principles (things chart library developers don't consider)

| Principle | Source | Why It's Novel |
|---|---|---|
| **Consumer contract / audience-aware rendering** | Theater | No chart library adapts output structure by audience role |
| **User inscription as first-class data** | Cartography + Military | Annotations are treated as decorations, not as the primary information layer |
| **Blind spot detection** | Military | No chart library shows what data is MISSING |
| **Structured judgment with confidence** | Military | Charts display data; intelligence products carry signed assessments |
| **Provenance as navigable tree** | Cuisine | No chart library lets you trace a derived chart back through transformations to source data |

### Convergent Principles (multiple domains independently)

| Convergence | Domains | Signal Strength |
|---|---|---|
| **Tiered output by consumer role** | All 4 | STRONGEST — every domain concluded this is the core gap |
| **Annotation by consumer** | Cartography + Theater + Military | 3/4 — the consumer's markings are often the point |
| **Rejection of capability inflation** | All 4 | Universal — more options ≠ more value |
| **Self-contained portable artifact** | Cuisine + Theater + Military | 3/4 — promote from feature to identity |
| **Threshold classification symbology** | Cartography + Military | 2/4 — visual encoding of pass/fail judgment |
| **Composed multi-artifact output** | Cuisine + Cartography | 2/4 — coordinated charts with shared framing |

### Reframing Insights

**Theater delivered the strongest reframe:** The problem is not missing chart types. The problem is a missing *directing layer* — something that sits above the rendering engine and decides what to show, how much, and in what order, based on who is watching. ForgeViz has actors and scripts but no director.

**Military Intelligence partially reframed:** A chart is not the deliverable. A *signed analytical product* is the deliverable. The chart is evidence within it.

## The Bottom Line

ForgeViz's gap is not rendering capability. 104 chart types is sufficient — all four domains said so independently. The gap is the layer between data and audience.

**What to build (in priority order):**

1. **Audience profiles** — a `consumer` parameter that changes chart selection, density, and presentation mode (executive/analyst/operator)
2. **Annotation layer** — user markings that persist, travel with the artifact, and are first-class data
3. **Composed reports** — multi-chart documents served as atomic units (not dashboards — documents)
4. **Threshold symbology** — visual encoding of pass/fail/warning as spatial property, not just reference lines

**What NOT to build:**
- More chart types (104 is enough — all 4 domains rejected count inflation)
- 3D perspective (not measurable — Cartography)
- Decorative animation (not informative — Cartography + Cuisine)
- Drag-and-drop builder (untrained noise — Military)
- Collaborative real-time editing (incoherent authorship — Cartography + Cuisine)
- AI auto-insights without attribution (unsigned intelligence — Military)
