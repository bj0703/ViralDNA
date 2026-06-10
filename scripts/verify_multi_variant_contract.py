from __future__ import annotations

from backend.app.core.multi_variant import (
    ensure_edit_timeline_variant_contract,
    ensure_final_video_multi_output,
    ensure_reference_variant_contract,
    ensure_resolved_gap_variant_contract,
    ensure_slot_match_variant_contract,
)


def main() -> None:
    reference_analysis = ensure_reference_variant_contract({
        "schema_version": "1.0",
        "template_id": "ref_001",
        "structural_slots": [{"slot_id": "hook_01", "role": "hook"}],
    })
    assert reference_analysis["default_variant_id"] == "structure"
    assert len(reference_analysis["variant_dimensions"]) == 4

    slot_matches = ensure_slot_match_variant_contract({
        "slot_assignments": [{"slot_id": "hook_01", "selected_candidate": {"asset_id": "asset_a"}}],
        "unfilled_slots": [],
        "low_confidence_slots": [],
        "matches": [{"slot": "hook_01", "material_id": "asset_a", "reason": "test"}],
        "gaps": [],
        "confidence": 0.8,
    }, reference_analysis=reference_analysis)
    assert slot_matches["default_variant_id"] == "structure"
    assert "variants" in slot_matches and len(slot_matches["variants"]) == 4
    assert slot_matches["slot_assignments"][0]["slot_id"] == "hook_01"

    resolved_gaps = ensure_resolved_gap_variant_contract({
        "resolved_gaps": [{"slot_id": "hook_01", "chosen_strategy": "reuse"}],
        "still_unresolved": [],
        "confidence": 0.7,
    })
    assert len(resolved_gaps["variants"]) == 4
    assert resolved_gaps["resolved_gaps"][0]["slot_id"] == "hook_01"

    edit_timeline = ensure_edit_timeline_variant_contract({
        "timeline_meta": {"duration": 12.0},
        "timeline": [{"clip_id": "clip_001", "slot_id": "hook_01", "start": 0.0, "end": 2.0}],
        "tracks": [{"track_id": "video_main", "segments": [{"clip_id": "clip_001"}]}],
        "validation": {"all_slots_filled": True},
    })
    assert len(edit_timeline["variants"]) == 4
    assert edit_timeline["timeline"][0]["clip_id"] == "clip_001"

    final_video_meta = ensure_final_video_multi_output({
        "default_variant_id": "structure",
        "outputs": [
            {"variant_id": "structure", "output_path": "a.mp4", "success": True},
            {"variant_id": "beat", "output_path": "b.mp4", "success": True},
        ],
    })
    assert final_video_meta["output_path"] == "a.mp4"
    assert len(final_video_meta["outputs"]) == 2

    print("multi-variant contract verification passed")


if __name__ == "__main__":
    main()
