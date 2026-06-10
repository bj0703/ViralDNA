## ADDED Requirements

### Requirement: Message input routes to create or re-submit based on job state
The system SHALL use a single message input entry point for both first-run orchestration and follow-up orchestration. If no active job exists, the message flow MUST create a new job; if an active job exists, the message flow MUST call the incremental `re-submit` API for that job.

#### Scenario: First message creates job
- **WHEN** the user sends a message while no active `currentJobId` exists
- **THEN** the frontend uses the job creation flow instead of calling `re-submit`

#### Scenario: Follow-up message re-submits active job
- **WHEN** the user sends a message while an active `currentJobId` exists
- **THEN** the frontend calls `POST /api/orchestration/jobs/{job_id}/re-submit`
- **THEN** the existing job remains the active job for the workbench

#### Scenario: SSE binds automatically after first-run creation
- **WHEN** a first-run job creation succeeds
- **THEN** the frontend automatically starts consuming that job’s SSE event stream
- **THEN** subsequent `plan_ready`, `step_start`, `step_write`, `step_skip`, and `step_fail` events update the right-side orchestration UI

### Requirement: Follow-up reference analysis honors the selected sample video
The system SHALL keep the selected reference video as part of the job interaction state so that follow-up analysis requests continue to target the user-selected sample video instead of always using the first uploaded reference video.

#### Scenario: Re-submit uses current selected reference target
- **WHEN** the user already has an active job and sends a follow-up request after selecting a different sample video
- **THEN** the request updates or carries the selected reference video identity for that job
- **THEN** downstream reference analysis uses that selected sample as the primary target
