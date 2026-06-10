from visual_supplement_skill import VisualSupplementSkill


def demo():
    skill = VisualSupplementSkill()

    sample_input = {
        "skill_name": "VisualSupplementSkill",
        "mode": "product_motion",
        "slot": {
            "slot_id": "highlight_01",
            "role": "highlight_01",
            "duration": 2.0,
            "creative_function": "产品高光展示",
            "information_function": "展示产品核心细节",
            "required_visual_type": ["产品特写", "细节展示"],
            "required_motion": ["slow_zoom", "push_in"],
            "shot_size": ["close_up"],
            "audio_sync": {
                "beat_position": "first_strong_beat",
                "sfx": "whoosh"
            },
            "transition_out": "zoom_cut"
        },
        "style_context": {
            "style_name": "产品展示",
            "type_label": "product展示",
            "color_tone": "clean / premium / bright",
            "caption_density": "low",
            "main_transitions": ["zoom_cut", "blur"]
        },
        "source_assets": {
            "reference_image": "https://your-domain/product_image_001.png",
            "available_segments_summary": [
                "已有产品正面图",
                "缺少产品旋转镜头",
                "缺少开头高光画面"
            ]
        },
        "generation_constraints": {
            "aspect_ratio": "9:16",
            "duration": 2.0,
            "avoid": ["水印", "品牌Logo变形", "人物脸部变形", "文字乱码"],
            "must_keep": ["产品主体清晰", "画面稳定", "运动幅度轻微"]
        }
    }

    result = skill.run(sample_input)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    demo()
