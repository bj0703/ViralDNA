## ADDED Requirements

### Requirement: 3-way concurrent asset indexing with per-asset immediate persistence
AssetIndexerAgent SHALL perform asset indexing with maximum 3 concurrent workers, and persist each asset analysis result immediately after completion rather than waiting for all assets to finish.

#### Scenario: 9 assets processed with max 3-way concurrency
- **WHEN** 9 asset videos are uploaded for indexing
- **THEN** The system SHALL use up to 3 concurrent workers to analyze the assets
- **AND** The total time SHALL be reduced by roughly 3x compared to serial processing

#### Scenario: Single asset finishes, immediately appended
- **WHEN** Any single asset finishes analysis
- **THEN** The result SHALL be immediately appended to `asset_index.assets`
- **AND** A `STEP_WRITE` event SHALL be logged in the shared memory event log

#### Scenario: Single asset fails, others continue
- **WHEN** A single asset analysis fails
- **THEN** The failed asset SHALL be marked with a warning
- **AND** The system SHALL continue processing remaining assets without interruption
