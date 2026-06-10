## ADDED Requirements

### Requirement: Asset indexer aligns with reference sample context
AssetIndexerAgent SHALL inject reference_analysis context before analyzing each asset video, ensuring alignment in direction with the reference sample. The injected context SHALL include:
- `type_label`: The type label extracted from reference sample
- `summary`: The narrative summary extracted from reference sample
- `migration_suggestion`: The migration suggestions extracted from reference sample

#### Scenario: Reference analysis exists and injected
- **WHEN** AssetIndexerAgent runs and `reference_analysis` is present in shared memory
- **THEN** The system SHALL inject the three fields as context prefix before calling the LLM for asset analysis

#### Scenario: Reference analysis does NOT exist, pure asset indexing
- **WHEN** AssetIndexerAgent runs and `reference_analysis` is NOT present in shared memory
- **THEN** The system SHALL skip injection and keep existing pure asset indexing behavior unchanged
