## ADDED Requirements

### Requirement: Orchestration uploads are accessible for real preview and playback
The system SHALL expose uploaded orchestration resources through stable read-only backend URLs so that the frontend can preview and play files associated with the active job.

#### Scenario: Uploaded sample video can be opened from frontend
- **WHEN** a reference video has been uploaded to an orchestration job
- **THEN** the frontend receives or derives a stable URL for that file
- **THEN** opening that URL returns the uploaded media content

#### Scenario: Uploaded material video can be opened from frontend
- **WHEN** a material video has been uploaded to an orchestration job
- **THEN** the frontend receives or derives a stable URL for that file
- **THEN** the workbench can use that URL for preview or playback

### Requirement: File delivery endpoint is limited to orchestration uploads
The system MUST restrict orchestration upload delivery to files inside the orchestration upload root and MUST NOT allow arbitrary filesystem reads.

#### Scenario: Reject path traversal outside upload root
- **WHEN** a client requests a file path that does not resolve inside the orchestration upload directory
- **THEN** the backend rejects the request instead of serving filesystem content
