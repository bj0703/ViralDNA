import os
import json
from typing import Dict, Any, List
from ark_client import ArkClient

BASE_DIR = os.path.dirname(__file__)
KB_ROOT = os.path.join(BASE_DIR, "knowledge_base")
STYLE_TEMPLATES_DIR = os.path.join(KB_ROOT, "style_templates")

SYSTEM_PROMPT = """你是一个短视频风格知识库生成器，目标是为一个"爆款视频迁移剪辑系统"生成小型结构化知识库。

系统背景：
用户可能没有上传样例视频，因此系统需要根据用户输入的风格需求，从知识库中检索风格模板，并生成可执行的剪辑结构。
你的任务不是写普通的剪辑教程，而是生成可以被 Agent 系统直接消费的 JSON 知识库。

核心要求：
1. 所有知识必须结构化，不能只写自然语言描述。
2. 每个风格模板必须能生成 structural_slots。
3. 每个 structural_slot 都要包含：
   - role
   - duration
   - creative_function
   - information_function
   - required_visual_type
   - required_motion
   - shot_size
   - caption_requirement
   - audio_sync
   - transition_out
   - importance
4. 风格模板要能指导素材匹配，而不是只描述风格。
5. 输出内容必须适合后续用于：风格检索、素材片段匹配、剪辑规划、字幕生成、转场选择、音效选择。
6. 不要生成无法执行的抽象词，比如"高级""丝滑""好看"必须落到具体规则上。
7. 输出必须是合法 JSON，不要包含 Markdown，不要解释。"""

STYLE_TEMPLATE_SCHEMA = r'''{
  "style_id": "",
  "style_name": "",
  "type_label": "",
  "aliases": [],
  "target_duration_range": [0, 0],
  "aspect_ratio": "9:16",
  "core_formula": "",
  "suitable_materials": [],
  "unsuitable_materials": [],
  "rhythm_structure": {
    "overall_pace": "",
    "avg_shot_duration_seconds": 0,
    "shot_switch_pacing": "",
    "highlight_position_ratio": [],
    "pace_changes_description": ""
  },
  "structural_slots": [
    {
      "slot_id": "",
      "role": "",
      "duration": 0,
      "creative_function": "",
      "information_function": "",
      "required_visual_type": [],
      "required_motion": [],
      "shot_size": [],
      "caption_requirement": {
        "need_caption": true,
        "style": "",
        "position": "",
        "semantic_role": "",
        "caption_formula_hint": ""
      },
      "audio_sync": {
        "beat_position": "",
        "sfx": ""
      },
      "transition_out": "",
      "importance": "",
      "match_priority": [],
      "copy_risk": ""
    }
  ],
  "caption_style_template": {
    "subtitle_density": "",
    "font_style": "",
    "keyword_highlight": true,
    "animation": "",
    "safe_area_preference": ""
  },
  "transition_style_template": {
    "main_transition_types": [],
    "usage_rule": "",
    "fallback_transition_types": []
  },
  "packaging_style_template": {
    "stickers": [],
    "cover_style": "",
    "color_tone": "",
    "visual_elements": ""
  },
  "transfer_rules": {
    "must_keep": [],
    "can_adapt": [],
    "must_not_copy": []
  },
  "fallback_strategy": [
    {
      "problem": "",
      "solution": ""
    }
  ],
  "embedding_text": ""
}'''

STYLE_ITEMS = [
    {
        "filename": "travel_transition.json",
        "style_id": "style_travel_001",
        "style_name": "高级感旅行转场",
        "type_label": "旅游转场",
        "target_duration": 18
    },
    {
        "filename": "vlog_travel.json",
        "style_id": "style_vlog_001",
        "style_name": "vlog旅拍",
        "type_label": "vlog旅拍",
        "target_duration": 20
    },
    {
        "filename": "talking_product.json",
        "style_id": "style_talking_001",
        "style_name": "口播带货",
        "type_label": "口播带货",
        "target_duration": 25
    },
    {
        "filename": "product_showcase.json",
        "style_id": "style_product_001",
        "style_name": "产品展示",
        "type_label": "product展示",
        "target_duration": 15
    },
    {
        "filename": "tutorial.json",
        "style_id": "style_tutorial_001",
        "style_name": "教程教学",
        "type_label": "教程教学",
        "target_duration": 30
    }
]


def build_style_prompt(item: Dict[str, Any]) -> str:
    return f"""请为短视频自动剪辑系统生成一个风格模板 JSON。

风格名称：{item['style_name']}
风格类型：{item['type_label']}
目标时长：{item['target_duration']} 秒
目标平台：抖音 / 小红书
画幅：9:16

要求：
1. style_id 填入 "{item['style_id']}"。
2. 输出一个完整 JSON 对象。
3. 该 JSON 必须能作为知识库中的 style_template 使用。
4. 必须包含 5 个 structural_slots：hook, context, highlight_01, highlight_02, ending。
5. 每个 slot 必须是可匹配、可执行、可剪辑的。
6. 每个 slot 必须描述需要什么类型的素材，而不是描述最终效果。
7. transition_out 必须使用具体可执行类型：cut / whip_pan / zoom_cut / blur / flash_black / flash_white / dissolve / fade_out。
8. audio_sync.beat_position 不能写 any，必须从以下选择：first_strong_beat / bar_change / transition_downbeat / phrase_release / weak_beat。
9. 字幕要求必须明确是否需要字幕、字幕位置、字幕语义功能。
10. 必须包含 fallback_strategy，用于素材不满足时的降级方案。
11. 输出必须是合法 JSON，不要 Markdown，不要解释。

JSON schema 如下：
{STYLE_TEMPLATE_SCHEMA}"""


def validate_style_template(obj: Dict[str, Any]) -> List[str]:
    problems = []
    required_fields = ["style_id", "style_name", "structural_slots"]
    for f in required_fields:
        if f not in obj:
            problems.append(f"缺少字段 {f}")
    slots = obj.get("structural_slots", [])
    if len(slots) != 5:
        problems.append(f"structural_slots 数量应为 5，实际 {len(slots)}")
    for idx, slot in enumerate(slots):
        if "transition_out" not in slot:
            problems.append(f"slot[{idx}] 缺少 transition_out")
        if "audio_sync" not in slot or "beat_position" not in slot.get("audio_sync", {}):
            problems.append(f"slot[{idx}] audio_sync.beat_position 不完整")
    return problems


def generate_editing_techniques(client: ArkClient) -> Dict[str, Any]:
    prompt = """请为短视频自动剪辑系统生成一个 editing_techniques.json。

目标：
生成一批可执行的剪辑技巧知识，用于 EditPlanner 根据风格模板和素材条件选择剪辑操作。

要求：
1. 输出 JSON 数组。
2. 总共生成 15 条技巧。
3. 包含以下类别：transition 6条，caption 4条，rhythm 3条，packaging 2条。
4. 每条技巧都必须包含：technique_id, name, category, compatible_styles, preconditions, execution_rule, fallback, embedding_text。
5. transition 类型必须从以下选择：cut / whip_pan / zoom_cut / blur / flash_black / flash_white / dissolve / fade_out。
6. 不要写抽象描述，必须写清楚适用条件和执行规则。
7. 输出必须是合法 JSON，不要 Markdown，不要解释。"""
    return client.generate_json(SYSTEM_PROMPT, prompt)


def generate_caption_formulas(client: ArkClient) -> Dict[str, Any]:
    prompt = """请为短视频自动剪辑系统生成一个 caption_formulas.json。

目标：
生成可用于不同风格、不同 slot 的字幕文案模板。这些模板不是最终文案，而是可填变量的公式。

要求：
1. 输出 JSON 数组。
2. 总共生成 30 条文案公式。
3. 数量分配：旅行/vlog 8条，口播带货 8条，产品展示 6条，教程教学 6条，通用结尾 2条。
4. 每条必须包含：formula_id, applicable_styles, slot_role, caption_type, template, variables, tone, avoid, embedding_text。
5. 文案必须适合短视频字幕，不能太长。
6. 不要出现具体品牌名。
7. 不要写侵权、夸大、绝对化表达。
8. 输出必须是合法 JSON，不要 Markdown，不要解释。"""
    return client.generate_json(SYSTEM_PROMPT, prompt)


def generate_matching_rules(client: ArkClient) -> Dict[str, Any]:
    prompt = """请为短视频自动剪辑系统生成一个 matching_rules.json。

目标：
定义 structural_slot 和用户素材 segment 的匹配规则。该规则用于 SlotMatcherAgent 给素材片段打分，并选择最适合填入每个 slot 的素材。

要求：
1. 输出一个 JSON 对象。
2. 必须包含：score_weights, hard_constraints, penalty_rules, fallback_rules, reuse_rules, transition_compatibility_rules。
3. score_weights 总和必须等于 1。
4. 规则必须可执行，不要写空泛描述。
5. 输出必须是合法 JSON，不要 Markdown，不要解释。"""
    return client.generate_json(SYSTEM_PROMPT, prompt)


def generate_asset_segment_schema(client: ArkClient) -> Dict[str, Any]:
    prompt = """请为短视频自动剪辑系统生成一个 asset_segment_schema.json。

目标：
定义用户上传素材被 AssetAnalyzerAgent 解析后的标准 segment 格式。该 schema 用于后续和 style_template 中的 structural_slots 做匹配。

要求：
1. 输出一个 JSON 对象。
2. 不需要生成真实素材，只需要生成 schema。
3. schema 字段必须覆盖：时间信息、内容摘要、视觉类型、主体、场景、景别、镜头运动、运动强度、情绪标签、质量分数、可用 slot、转场适配性、字幕安全区、embedding_text。
4. 输出必须是合法 JSON，不要 Markdown，不要解释。"""
    return client.generate_json(SYSTEM_PROMPT, prompt)


def main():
    client = ArkClient()
    print("[开始] 生成知识库...")

    for item in STYLE_ITEMS:
        print(f"-> 生成风格模板: {item['style_name']}")
        obj = client.generate_json(SYSTEM_PROMPT, build_style_prompt(item))
        problems = validate_style_template(obj)
        if problems:
            print(f"   警告: {problems}")
        out_path = os.path.join(STYLE_TEMPLATES_DIR, item["filename"])
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        print(f"   已写入: {out_path}")

    print("-> 生成 editing_techniques.json")
    editing = generate_editing_techniques(client)
    with open(os.path.join(KB_ROOT, "editing_techniques.json"), "w", encoding="utf-8") as f:
        json.dump(editing, f, ensure_ascii=False, indent=2)
    print("   已写入")

    print("-> 生成 caption_formulas.json")
    caption = generate_caption_formulas(client)
    with open(os.path.join(KB_ROOT, "caption_formulas.json"), "w", encoding="utf-8") as f:
        json.dump(caption, f, ensure_ascii=False, indent=2)
    print("   已写入")

    print("-> 生成 matching_rules.json")
    matching = generate_matching_rules(client)
    with open(os.path.join(KB_ROOT, "matching_rules.json"), "w", encoding="utf-8") as f:
        json.dump(matching, f, ensure_ascii=False, indent=2)
    print("   已写入")

    print("-> 生成 asset_segment_schema.json")
    schema = generate_asset_segment_schema(client)
    with open(os.path.join(KB_ROOT, "asset_segment_schema.json"), "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)
    print("   已写入")

    print("[完成] 全部知识库文件生成完毕！")


if __name__ == "__main__":
    main()
