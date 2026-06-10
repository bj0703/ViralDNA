## ADDED Requirements

### Requirement: System SHALL derive four edit variants from one reference analysis
The system SHALL use one completed reference analysis as the shared source of truth and derive exactly four edit variants named `structure`, `beat`, `transition`, and `rhythm`. Each variant SHALL represent a different downstream matching and planning preference rather than a separate reference-analysis job.

#### Scenario: Reference analysis completes successfully
- **WHEN** the reference analysis output contains usable structural slots and timing metadata
- **THEN** the system creates four named variant branches for downstream slot matching and planning

#### Scenario: Downstream components consume variant definitions
- **WHEN** a downstream agent reads the reference-analysis-driven edit context
- **THEN** it receives stable variant identifiers and can distinguish structure-first, beat-first, transition-first, and rhythm-first behaviors

### Requirement: System SHALL output slot matches per variant
The system SHALL generate slot-matching results for each edit variant and expose them in a machine-readable `variants` container while preserving a default variant compatibility view for existing consumers.

#### Scenario: Slot matching succeeds for all variants
- **WHEN** the slot matcher finishes processing available assets against the shared structural slots
- **THEN** the output includes per-variant slot assignments, unfilled slots, low-confidence slots, and confidence values for all four variants

#### Scenario: Existing consumer reads legacy slot-match fields
- **WHEN** a consumer requests the top-level slot-match fields without variant awareness
- **THEN** the system returns the default variant view instead of failing due to the new multi-variant structure

### Requirement: System SHALL resolve gaps and plan timelines per variant
The system SHALL generate gap-resolution results and editable timelines independently for each edit variant while keeping the default variant accessible through backward-compatible top-level fields.

#### Scenario: A variant has unfilled slots
- **WHEN** one variant cannot fully match all structural slots from available assets
- **THEN** the system produces gap-resolution output for that specific variant without overwriting the gap decisions of other variants

#### Scenario: Timeline planning completes
- **WHEN** the edit planner finishes for a job with four variant match sets
- **THEN** the system stores four timeline results keyed by variant identifier and exposes a default top-level timeline view for compatibility

### Requirement: System SHALL render and return multiple final outputs
The system SHALL render final videos per variant and return a multi-output result set that includes per-variant file metadata, success state, and retrievable output URLs.

#### Scenario: All variants render successfully
- **WHEN** final rendering completes for a job
- **THEN** the system returns four output entries, one for each variant, with stable identifiers and output file references

#### Scenario: A subset of variants fails to render
- **WHEN** one or more variant timelines fail during rendering
- **THEN** the system preserves successful variant outputs, reports failed variants explicitly, and does not discard the successful results

### Requirement: Result workbench SHALL support variant switching
The result-video workbench SHALL allow the user to switch between the four edit variants and inspect the corresponding rendered video, timeline, slot-match explanation, gap-resolution explanation, and validation summary for the selected variant.

#### Scenario: User opens the result tab after a multi-variant job
- **WHEN** the result tab receives multi-variant timeline and render data
- **THEN** the UI displays a variant switcher and updates the rest of the result panel to match the selected variant

#### Scenario: User opens the result tab for legacy single-variant data
- **WHEN** the result tab receives only legacy single-result fields
- **THEN** the UI falls back to the existing single-version presentation instead of breaking
