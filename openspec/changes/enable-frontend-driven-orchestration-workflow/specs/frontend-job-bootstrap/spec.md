## ADDED Requirements

### Requirement: User can create a job entirely from the frontend
The system SHALL allow a user to create a new orchestration job from the frontend without using Swagger or any manual backend tooling. The first submission MUST include the initial natural-language intent and any currently selected reference/material videos.

#### Scenario: Create job from first message
- **WHEN** the user has no current job and sends the first request from the frontend
- **THEN** the frontend submits the request to the job creation API
- **THEN** the backend returns a new `job_id`
- **THEN** the frontend stores that `job_id` as the active job for the whole workbench

#### Scenario: Create job with selected files
- **WHEN** the user has selected one or more reference or material videos before the first submission
- **THEN** the first job creation request includes those files and their reference/material classification
- **THEN** the created job persists the uploaded files in shared memory as `inputs.uploaded_videos`

#### Scenario: Preserve pending state on create failure
- **WHEN** the initial job creation request fails
- **THEN** the frontend shows a clear failure message
- **THEN** the user’s selected files and unsent first prompt remain available for retry

### Requirement: Selected reference video determines the primary analysis target
The system SHALL allow only one selected reference video at a time in the frontend, and that explicit selection MUST determine which sample video the backend treats as the primary reference target when multiple reference videos exist.

#### Scenario: User selects one reference video among many
- **WHEN** multiple reference videos are visible in the sample video area
- **THEN** clicking one video marks it as the single selected reference target
- **THEN** any previously selected reference video is deselected

#### Scenario: First submission carries selected reference target
- **WHEN** the user creates a new job while a reference video is selected
- **THEN** the first request includes the selected reference video identity
- **THEN** the backend persists that selection in shared memory for the created job

#### Scenario: Invalid selected reference falls back safely
- **WHEN** the stored selected reference video no longer exists in the job uploads
- **THEN** the backend falls back to the first available reference video instead of failing the whole analysis flow
