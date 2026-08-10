# ChemSafe hazard incompatibility rule set

**Purpose of this document.** Every automated "storage incompatibility" alert
ChemSafe raises must be traceable back to a stated, defensible safety
principle — not an arbitrary if/else branch. This document is that trace: it
is the single source of truth the code implements against, and it is written
so it can be read, quoted, or adapted directly for a project write-up or
defense.

## 1. Scope and simplification (read this first)

ChemSafe classifies each chemical into **one of 8 broad hazard classes**:
`none, flammable, corrosive, toxic, oxidizer, reactive, health, environmental`.

The real GHS (Globally Harmonized System) classifies substances at a much
finer grain — e.g. "flammable" alone splits into flammable gases, aerosols,
liquids (further split into 4 categories by flash point), and solids; "health
hazard" covers 10 distinct endpoints (acute toxicity, carcinogenicity,
reproductive toxicity, sensitization, etc.) each with their own hazard
statements (H-codes) and precautionary statements (P-codes).

**This project deliberately works at the broad-class level, not the
H-code level.** That's a scope decision, not an oversight, made for two
reasons appropriate to a final-year project: (1) matching every H-code
combination against every other would require encoding hundreds of GHS
hazard-statement pairs, which is disproportionate to the project's aim of
demonstrating a working rule-based hazard engine; (2) the `chemicals.ghs_category`
field already stores the specific H-codes per chemical (e.g. `H225`, `H314`)
for display and reference — the incompatibility *engine* reasons over the
coarser `hazard_class`, while the underlying H-codes remain visible to the
user for their own judgement.

**State this simplification explicitly in your write-up.** It's the one
place a reviewer might expect full GHS granularity; the honest answer is
"implemented at hazard-class granularity by design, with H-codes retained as
reference data," not "the system doesn't know about H-codes."

## 2. Where these principles come from

The rules below are not manufacturer- or substance-specific; they encode
**general laboratory chemical segregation principles** that are consistently
taught and documented across widely-used chemical safety references,
including:

- OSHA's Laboratory Standard (29 CFR 1910.1450) and general segregation
  guidance for oxidizers, flammables, and corrosives.
- NFPA hazardous-materials storage/segregation guidance.
- The NOAA/CAMEO chemical compatibility chart (a standard reference for
  which broad hazard categories should not be co-stored).
- Common chemical-supplier storage colour-coding systems (e.g. Flinn
  Scientific's storage groups), which are built around exactly these
  class-level pairings (flammable vs. oxidizer vs. corrosive vs. reactive).

These are **general principles**, cited generically rather than by exact
clause number, because this project reasons at hazard-class granularity, not
at the level of a specific regulatory citation for a specific compound. If
your institution requires a specific regulatory citation, verify the exact
clause against your local/regional standard before quoting it in your
defense — don't take a specific section number from this document, because
none is asserted here.

## 3. Implemented rules

Each rule fires when **two chemicals sharing the same `location` value**
have hazard classes matching the pair below (order-independent).

| # | Hazard pair | Severity | Principle | Rationale | Recommended corrective action |
|---|---|---|---|---|---|
| R1 | flammable × oxidizer | **Critical** | Oxidizer–flammable segregation | Oxidizers supply or generate oxygen and dramatically accelerate combustion; co-storage with flammable material is one of the most universally cited fire/explosion risks in lab safety guidance. | Relocate one substance immediately to a dedicated, separate storage area. Oxidizers must not share a cabinet, shelf, or spill-containment tray with any flammable liquid or solid. |
| R2 | oxidizer × reactive | **Critical** | Oxidizer–reactive segregation | Reactive substances (water-reactive, pyrophoric, or self-reactive materials) can react violently with oxidizers or have their decomposition accelerated by them, risking an uncontrolled exotherm. | Isolate the reactive substance in dedicated, manufacturer-specified storage (e.g. inert atmosphere or mineral oil as directed by its SDS), physically separate from all oxidizers. |
| R3 | flammable × reactive | **High** | Flammable–reactive segregation | Reactive substances can generate heat, sparks, or spontaneous ignition, which is sufficient to ignite nearby flammable material. | Store reactive materials away from all flammable liquids/solids; confirm storage conditions against the reactive substance's SDS. |
| R4 | corrosive × reactive | **High** | Corrosive–reactive segregation | Corrosives (notably aqueous acids/bases) can react violently with water-reactive or active-metal-sensitive materials — generating heat, flammable gas (e.g. hydrogen), or a violent neutralization exotherm. | Store in separate secondary containment; do not combine without a documented risk assessment and appropriate engineering controls. |
| R5 | corrosive × oxidizer | **High** | Corrosive–oxidizer segregation | Some concentrated corrosive acids are themselves strong oxidizers or react with other oxidizers, releasing heat or toxic gas. | Maintain separate acid and oxidizer storage (e.g. dedicated acid cabinet), per standard chemical storage segregation practice. |
| R6 | toxic × oxidizer | **Medium** | Toxic-release acceleration | An oxidizer reacting nearby can accelerate the release, volatilization, or violent dispersal of a toxic substance in the event of a spill or fire, compounding the incident. | Store separately; ensure fume-hood ventilation is available wherever both hazard classes are handled in proximity. |
| R7 | toxic × corrosive | **Medium** | Compounded exposure / spill-response complexity | Co-locating toxic and corrosive substances compounds first-aid response (simultaneous chemical burn + systemic toxic exposure) and complicates spill cleanup and PPE selection. | Segregate storage; keep substance-specific spill kits and SDS co-located with each chemical, not shared. |

## 4. Explicitly out of scope (and why)

Rather than inventing a rule for all 28 possible hazard-class pairs, the
following are deliberately **not** implemented, with the reasoning stated so
it can't be mistaken for an oversight:

- **`none` paired with anything** — by definition, a chemical classified
  `none` carries no significant recognized hazard; no general segregation
  principle applies.
- **`health` in most pairings** — our `health` class is a catch-all for
  chronic/health-endpoint hazards (e.g. reproductive toxicity, carcinogenicity)
  that, unlike the acute physical hazards above, don't have a single
  universally-standard *storage segregation* principle the way
  flammable/oxidizer/corrosive/reactive combinations do. Encoding one would
  mean asserting a rule not genuinely backed by common guidance. `health`
  chemicals still receive standard "handle with strict controls" treatment
  elsewhere in the system (see the existing per-chemical severity view in
  `hazards.tsx`) — they're just not part of the *pairwise* incompatibility
  engine.
- **`environmental` pairings** — this class is predominantly about
  containment/disposal risk (aquatic toxicity on release) rather than an
  acute co-storage reaction risk, so it isn't paired here either.

If your project documentation calls for broader coverage than R1–R7, this is
the section to revise — and the reasoning above is the explanation to give
for why the current set stops where it does.

## 5. How this maps to the implementation

- `hazards.IncompatibilityRule` gains two new fields to carry this table
  faithfully: `principle` (short name, e.g. "Oxidizer–flammable segregation")
  and `recommended_action` (the corrective-action text) — `severity` and
  `reason` already exist.
- A seed command populates exactly R1–R7 above — no more, no less — so the
  seeded data *is* this table, not an approximation of it.
- The detection engine groups chemicals by `location`, checks each pair
  against `IncompatibilityRule` (both orderings), and raises one `Alert`
  (`alert_type=incompatibility`) per violating pair, per location, carrying:
  the two chemicals involved (id + name + hazard_class each), the matched
  rule's `principle`, `reason`, `severity`, and `recommended_action`, and the
  shared `location`. Every field the alert exposes is a direct pointer back
  into this document — nothing is synthesized at alert-generation time.
