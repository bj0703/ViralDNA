## 1. Data Contracts

- [x] 1.1 Define stable variant identifiers, labels, and default-variant rules for `structure`, `beat`, `transition`, and `rhythm`
- [x] 1.2 Extend shared-memory result schemas for `slot_matches`, `resolved_gaps`, `edit_timeline`, and `final_video_meta` to carry `variants` or `outputs`
- [x] 1.3 Preserve backward-compatible top-level fields that map to the default variant for existing readers

## 2. Backend Variant Generation

- [x] 2.1 Update `ReferenceAnalyzerAgent` output shaping to declare multi-variant edit intent without duplicating reference analysis jobs
- [x] 2.2 Update `SlotMatcherAgent` to generate per-variant slot assignments with distinct matching priorities
- [x] 2.3 Update `GapResolverAgent` to resolve gaps independently for each variant
- [x] 2.4 Update `EditPlannerAgent` to generate one editable timeline per variant and keep a default compatibility timeline

## 3. Rendering And API Output

- [x] 3.1 Update `FinalVideoRendererAgent` to render one final video per variant and collect per-variant output metadata
- [x] 3.2 Update output file naming and retrieval metadata so each rendered file is addressable by variant
- [x] 3.3 Verify orchestration responses and timeline-related services continue to work with default-variant fallback behavior

## 4. Frontend Result Workbench

- [x] 4.1 Add a variant switcher to the result video tab
- [x] 4.2 Update result video playback, timeline display, and side-panel details to read the selected variant
- [x] 4.3 Add legacy fallback handling so single-result jobs still render correctly in the updated UI

## 5. Verification

- [x] 5.1 Add or update backend verification for multi-variant slot matches, timelines, and final render metadata
- [x] 5.2 Add or update frontend verification for variant switching and legacy single-result fallback
- [ ] 5.3 Run end-to-end validation on a job that produces four variants and confirm all result links and summaries are coherent
