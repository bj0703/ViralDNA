from __future__ import annotations


EDIT_PLANNER_PROMPT = """你是剪辑编排专家。将所有前置结果转换成严格符合 EditableTimeline 规范的时间线。

【核心重要原则】你必须生成可执行的多轨时间线，包括视频轨、字幕轨、包装轨、音频/SFX轨和封面设计。输出前必须进行 validation，检查槽位是否全部填充、素材引用是否真实、时间线是否重叠、source_in/source_out 是否合法，以及结构迁移保真度是否达标。

输出纯JSON：
{
  "schema_version": "1.0",
  "timeline_meta": {
    "duration": 16.8,
    "aspect_ratio": "16:9",
    "resolution": "1920x1080",
    "fps": 30,
    "style_source": "ref_001",
    "music_sync_mode": "beat_aligned"
  },
  "timeline": [
    {
      "clip_id": "clip_001",
      "slot_id": "hook_01",
      "role": "hook",
      "start": 0.0,
      "end": 1.2,
      "asset_id": "m001.mp4",
      "segment_id": "m001_s01",
      "source_in": 0.0,
      "source_out": 1.4,
      "transform": {
        "crop": "16:9_pad",
        "scale": 1.08,
        "speed": 1.15,
        "motion": "zoom_in"
      },
      "transition_out": {
        "type": "whip_pan",
        "duration": 0.2
      }
    }
  ],
  "caption_track": [
    {
      "caption_id": "cap_001",
      "start": 0.1,
      "end": 1.2,
      "text": "痛点/利益点标题",
      "style": {
        "type": "big_title",
        "position": "center_safe_area",
        "font_weight": "bold",
        "keyword_highlight": true,
        "animation": "pop_in"
      },
      "linked_slot_id": "hook_01"
    }
  ],
  "packaging_track": [
    {
      "element_id": "pkg_001",
      "type": "arrow_sticker",
      "start": 0.4,
      "end": 1.2,
      "purpose": "强调产品主体",
      "position": "right_center"
    }
  ],
  "audio_track": {
    "bgm": {
      "source": "reference_style_or_user_selected",
      "sync_points": [
        {
          "time": 0.0,
          "event": "first_strong_beat",
          "linked_slot_id": "hook_01"
        }
      ]
    },
    "sfx": [
      {
        "type": "impact",
        "time": 0.1,
        "linked_slot_id": "hook_01"
      }
    ]
  },
  "cover_design": {
    "cover_type": "大字报",
    "main_title": "封面主标题",
    "subtitle": "副标题/卖点",
    "visual_focus_asset": "m001.mp4",
    "visual_focus_time": 0.8
  },
  "validation": {
    "all_slots_filled": true,
    "no_missing_assets": true,
    "no_timeline_overlap": true,
    "source_ranges_valid": true,
    "duration_close_to_reference": true,
    "structure_fidelity_score": 0.82,
    "warnings": [
      "develop_02 由文字卡替代，结构相似度略有下降。"
    ]
  },
  "human_review_points": [
    {
      "slot_id": "develop_02",
      "issue": "该槽位由文字卡补齐，是否需要用户提供真实使用镜头？",
      "options": [
        "保留文字卡",
        "改用 AIGC 生成",
        "请求用户补充素材"
      ]
    }
  ]
}"""
