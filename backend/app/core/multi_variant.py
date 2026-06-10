from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping, Optional

DEFAULT_VARIANT_ID = "structure"
VARIANT_ORDER = ["structure", "beat", "transition", "rhythm"]

VARIANT_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "structure": {
        "variant_id": "structure",
        "label": "结构优先版",
        "matching_focus": ["role", "information_function", "required_visual_type"],
        "planning_focus": ["slot_order", "story_fidelity"],
    },
    "beat": {
        "variant_id": "beat",
        "label": "卡点优先版",
        "matching_focus": ["beat_position", "duration_fit", "motion_fit"],
        "planning_focus": ["beat_alignment", "cut_density"],
    },
    "transition": {
        "variant_id": "transition",
        "label": "转场优先版",
        "matching_focus": ["transition_out", "adjacent_compatibility"],
        "planning_focus": ["transition_style_consistency"],
    },
    "rhythm": {
        "variant_id": "rhythm",
        "label": "节奏优先版",
        "matching_focus": ["pace", "shot_density", "energy_curve"],
        "planning_focus": ["rhythm_curve_fidelity"],
    },
}


def get_default_variant_id(data: Optional[Mapping[str, Any]] = None) -> str:
    default_variant_id = data.get("default_variant_id") if isinstance(data, Mapping) else None
    if isinstance(default_variant_id, str) and default_variant_id in VARIANT_DEFAULTS:
        return default_variant_id
    return DEFAULT_VARIANT_ID


def get_variant_catalog(reference_analysis: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    catalog = {variant_id: deepcopy(spec) for variant_id, spec in VARIANT_DEFAULTS.items()}
    existing = reference_analysis.get("variant_dimensions") if isinstance(reference_analysis, Mapping) else None
    if isinstance(existing, list):
        for item in existing:
            if not isinstance(item, Mapping):
                continue
            variant_id = item.get("variant_id")
            if not isinstance(variant_id, str) or variant_id not in catalog:
                continue
            catalog[variant_id].update(deepcopy(dict(item)))
    return [catalog[variant_id] for variant_id in VARIANT_ORDER]


def ensure_reference_variant_contract(reference_analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    result = deepcopy(reference_analysis) if isinstance(reference_analysis, dict) else {}
    result["default_variant_id"] = get_default_variant_id(result)
    result["variant_dimensions"] = get_variant_catalog(result)
    return result


def get_variant_payload(data: Optional[Mapping[str, Any]], variant_id: Optional[str] = None) -> Dict[str, Any]:
    if not isinstance(data, Mapping):
        return {}

    variants = data.get("variants")
    selected_variant_id = variant_id or get_default_variant_id(data)
    if isinstance(variants, Mapping):
        payload = variants.get(selected_variant_id) or variants.get(get_default_variant_id(data))
        if isinstance(payload, Mapping):
            return deepcopy(dict(payload))

    return deepcopy(dict(data))


def attach_variants(
    base_payload: Optional[Dict[str, Any]],
    variant_payloads: Mapping[str, Dict[str, Any]],
    *,
    default_variant_id: str = DEFAULT_VARIANT_ID,
    compatibility_keys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    result = deepcopy(base_payload) if isinstance(base_payload, dict) else {}
    result["schema_version"] = "2.0"
    result["default_variant_id"] = default_variant_id

    variants: Dict[str, Dict[str, Any]] = {}
    for variant_spec in get_variant_catalog(result):
        variant_id = variant_spec["variant_id"]
        payload = deepcopy(variant_payloads.get(variant_id) or variant_payloads.get(default_variant_id) or {})
        payload.setdefault("variant_id", variant_id)
        payload.setdefault("label", variant_spec["label"])
        payload.setdefault("matching_focus", deepcopy(variant_spec.get("matching_focus", [])))
        payload.setdefault("planning_focus", deepcopy(variant_spec.get("planning_focus", [])))
        variants[variant_id] = payload
    result["variants"] = variants

    default_payload = variants.get(default_variant_id, {})
    for key in compatibility_keys or []:
        if key in default_payload:
            result[key] = deepcopy(default_payload[key])
    return result


def ensure_slot_match_variant_contract(
    data: Optional[Dict[str, Any]],
    *,
    reference_analysis: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    payload = deepcopy(data) if isinstance(data, dict) else {}
    variant_catalog = get_variant_catalog(reference_analysis)
    variants = payload.get("variants")
    if not isinstance(variants, Mapping):
        variants = {get_default_variant_id(payload): deepcopy(payload)}
    variant_payloads = {
        variant_id: deepcopy(dict(value))
        for variant_id, value in variants.items()
        if isinstance(value, Mapping)
    }
    result = attach_variants(
        payload,
        variant_payloads,
        default_variant_id=get_default_variant_id(payload),
        compatibility_keys=[
            "template_id",
            "slot_assignments",
            "shot_matches",
            "unfilled_slots",
            "low_confidence_slots",
            "confidence",
            "matches",
            "gaps",
        ],
    )
    result["variant_dimensions"] = variant_catalog
    return result


def ensure_resolved_gap_variant_contract(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = deepcopy(data) if isinstance(data, dict) else {}
    variants = payload.get("variants")
    if not isinstance(variants, Mapping):
        variants = {get_default_variant_id(payload): deepcopy(payload)}
    variant_payloads = {
        variant_id: deepcopy(dict(value))
        for variant_id, value in variants.items()
        if isinstance(value, Mapping)
    }
    return attach_variants(
        payload,
        variant_payloads,
        default_variant_id=get_default_variant_id(payload),
        compatibility_keys=["resolved_gaps", "still_unresolved", "confidence"],
    )


def ensure_edit_timeline_variant_contract(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = deepcopy(data) if isinstance(data, dict) else {}
    variants = payload.get("variants")
    if not isinstance(variants, Mapping):
        variants = {get_default_variant_id(payload): deepcopy(payload)}
    variant_payloads = {
        variant_id: deepcopy(dict(value))
        for variant_id, value in variants.items()
        if isinstance(value, Mapping)
    }
    return attach_variants(
        payload,
        variant_payloads,
        default_variant_id=get_default_variant_id(payload),
        compatibility_keys=[
            "base_timeline",
            "timeline_meta",
            "timeline",
            "tracks",
            "caption_track",
            "packaging_track",
            "audio_track",
            "cover_design",
            "validation",
            "human_review_points",
            "confidence",
        ],
    )


def ensure_final_video_multi_output(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = deepcopy(data) if isinstance(data, dict) else {}
    default_variant_id = get_default_variant_id(payload)
    outputs = payload.get("outputs")
    if isinstance(outputs, list):
        normalized_outputs = []
        for item in outputs:
            if not isinstance(item, Mapping):
                continue
            output_item = deepcopy(dict(item))
            variant_id = output_item.get("variant_id")
            if not isinstance(variant_id, str):
                continue
            output_item.setdefault("label", VARIANT_DEFAULTS.get(variant_id, {}).get("label", variant_id))
            normalized_outputs.append(output_item)
        payload["outputs"] = normalized_outputs
        if normalized_outputs:
            default_output = next(
                (item for item in normalized_outputs if item.get("variant_id") == default_variant_id),
                normalized_outputs[0],
            )
            for key in [
                "output_path",
                "output_url",
                "output_filename",
                "file_size_bytes",
                "rendered_segment_count",
                "success",
                "rendered_at",
            ]:
                if key in default_output:
                    payload[key] = deepcopy(default_output[key])
        payload["default_variant_id"] = default_variant_id
        return payload

    legacy_output = deepcopy(payload)
    legacy_output.setdefault("variant_id", default_variant_id)
    legacy_output.setdefault("label", VARIANT_DEFAULTS[default_variant_id]["label"])
    payload["outputs"] = [legacy_output]
    payload["default_variant_id"] = default_variant_id
    return payload
