## ADDED Requirements

### Requirement: Workbench tabs render backend orchestration outputs
The system SHALL render the middle workbench tabs from backend orchestration data instead of static mock content. The frontend MUST use the active job’s shared memory state as the source of truth for initial rendering.

#### Scenario: Sample tab renders reference analysis
- **WHEN** the active job contains `reference_analysis` in shared memory
- **THEN** the sample tab renders that analysis instead of placeholder mock content

#### Scenario: Material tab renders asset index
- **WHEN** the active job contains `asset_index` in shared memory
- **THEN** the material tab renders indexed material assets instead of placeholder mock content

#### Scenario: Result tab renders timeline outputs
- **WHEN** the active job contains `slot_matches`, `edit_timeline`, or `final_video_meta`
- **THEN** the result tab renders those outputs instead of placeholder mock content

### Requirement: Workbench stays bound to the active job
The system SHALL keep the middle workbench synchronized with the same active `currentJobId` used by the left and right panels.

#### Scenario: Switching to a created job hydrates workbench state
- **WHEN** a new job becomes the active `currentJobId`
- **THEN** the workbench loads that job’s latest shared memory snapshot
- **THEN** all three tabs reflect that same active job context

#### Scenario: Agent completion refreshes workbench content
- **WHEN** the active job receives new orchestration output through completed agent steps
- **THEN** the workbench refreshes the affected tab content without requiring a full page reload
