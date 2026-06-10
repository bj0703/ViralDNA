下面是一份**完整修改方案**，可以直接作为你这个“爆款视频结构迁移”项目的 agent 重构方案使用。

你的现有五个 agent 已经覆盖了基本链路：Reference Analyzer 负责样例视频拆解，Asset Indexer 负责素材分析，Slot Matcher 做素材与槽位匹配，Gap Resolver 处理素材缺口，Edit Planner 生成时间线。当前问题主要是：**分析结果偏报告化，缺少统一结构槽位；素材分析粒度不够细；匹配逻辑不够结构驱动；缺口补齐不够可执行；最终时间线缺少校验与人机协同入口。** 例如，Reference Analyzer 已经要求分析 hook/develop/cta、节奏、字幕、转场、BGM 等内容，但还没有输出后续可直接匹配的标准化 structural slots。 Asset Indexer 目前虽然有 usable_segments，但字段仍偏粗。

---

# 爆款视频结构迁移系统完整修改方案

## 一、修改总目标

本次修改的核心目标是：

> 将系统从“样例视频分析 + 素材匹配”升级为“创作结构抽象 + 新内容迁移生成”。

也就是说，系统不应该直接复制样例视频里的具体内容，而应该抽象出样例视频的**创作方法**，包括：

* 开头如何吸引用户；
* 镜头如何推进信息；
* 字幕如何强化卖点；
* 包装如何制造情绪；
* 转场如何连接画面；
* 音乐如何卡点；
* 结尾如何完成转化；
* 素材不足时如何补齐或重排结构。

最终系统应该形成如下链路：

```text
样例视频
  ↓
Reference Analyzer：提取可迁移结构模板
  ↓
用户素材
  ↓
Asset Indexer：建立素材片段库
  ↓
Slot Matcher：把素材片段填入结构槽位
  ↓
Gap Resolver：处理缺失槽位
  ↓
Edit Planner：生成可执行剪辑时间线
  ↓
Verifier / Human Review：检查结构迁移质量与人工可控点
```

---

# 二、总体架构修改

## 原始架构

```text
Reference Analyzer
Asset Indexer
Slot Matcher
Gap Resolver
Edit Planner
```

## 修改后架构

```text
1. Reference Analyzer
   样例视频 → 可迁移结构模板

2. Asset Indexer
   用户素材 → 可剪辑片段库

3. Slot Matcher
   结构槽位 × 素材片段 → 槽位填充方案

4. Gap Resolver
   未填充槽位 → 结构重排 / 文案补全 / 包装补全 / AIGC 补全 / 素材复用

5. Edit Planner
   槽位填充方案 → EditableTimeline

6. Verifier / Human Review，建议新增
   检查结构迁移是否成功，并输出人工可调整点
```

第六个 agent 不是必须单独实现，也可以并入 Edit Planner。但从课题表达上看，加入这个模块会更好，因为课题强调“更智能、更可控的视频创作方案”。

---

# 三、统一中间数据协议

这是最重要的修改。

当前五个 agent 的 JSON 字段还没有完全对齐。例如 Slot Matcher 的补全建议里有 `web_search`，但 Gap Resolver 的策略列表里没有这个策略，Gap Resolver 使用的是 reuse、static_graphic、text_card、brand_asset、ai_generate、ask_user 六级优先级。 

建议统一成下面这套核心概念。

---

## 1. 统一 slot_id 格式

所有 agent 都使用同一种槽位 ID：

```text
hook_01
hook_02
develop_01
develop_02
cta_01
```

不要混用：

```text
hook_1
hook_01
slot_001
develop_2
develop_02
```

推荐格式：

```json
{
  "slot_id": "hook_01",
  "role": "hook"
}
```

---

## 2. 统一缺口补齐策略

建议把 Gap Resolver 的策略改成下面七类：

```text
reuse              复用已有素材，裁剪 / 变速 / 放大 / 冻帧
static_graphic     静态图动效，Ken Burns / 视差 / 放大推进
text_card          文字卡 / 卖点卡 / 痛点卡
brand_asset        品牌素材包装，Logo / 产品图 / KV / 贴纸
structure_reorder  结构重排，删减、合并、替换某些槽位
ai_generate        AIGC 生成补充素材
ask_user           请求用户补充素材
```

建议去掉 Slot Matcher 里的 `web_search`，因为课题主要强调用户素材、AIGC、包装和人机协同，不一定需要网络素材检索。如果确实要保留，也应该放到 `external_asset_search`，但不建议作为主策略。

---

## 3. 统一置信度字段

所有 agent 输出都建议加入：

```json
{
  "confidence": 0.85,
  "risk_notes": []
}
```

这样方便后续筛选低置信度结果，并交给人工确认。

---

# 四、五个 agent 的具体修改方案

---

# 1. Reference Analyzer 修改方案

## 当前问题

Reference Analyzer 现在已经做了三类分析：

* 脚本结构；
* 节奏结构；
* 包装与声音。

并且要求忽略水印、裁剪无效片尾，这个设计是很好的。
但当前输出仍然偏“分析报告”，不够适合作为后续 agent 的结构模板。

## 修改目标

Reference Analyzer 要从“视频分析师”升级为：

> 爆款结构模板抽象器。

它不仅要说这个视频是什么内容，还要输出：

* 每个镜头/片段承担什么创作功能；
* 每个槽位需要什么类型的新素材；
* 哪些结构必须保留；
* 哪些具体内容不能复制；
* 节奏、字幕、转场、音乐如何迁移。

## 新增核心字段

建议新增：

```json
{
  "schema_version": "1.0",
  "template_id": "ref_001",
  "structural_slots": [],
  "rhythm_curve": [],
  "audio_beat_map": [],
  "caption_style_template": {},
  "transition_style_template": {},
  "packaging_style_template": {},
  "transfer_rules": {},
  "human_review_notes": []
}
```

## 推荐输出结构

```json
{
  "schema_version": "1.0",
  "template_id": "ref_001",
  "video_basic_info": {
    "file_total_duration_seconds": 18.6,
    "core_content_effective_duration_seconds": 16.8,
    "outro_start_time_seconds": null,
    "type_label": "口播带货"
  },
  "script_structure": {
    "summary": "先用痛点制造停留，再展示解决方案，最后用明确 CTA 推动行动。",
    "paragraphs": [
      {
        "type": "hook",
        "start_time": 0.0,
        "end_time": 3.0,
        "content_summary": "开头用强痛点字幕和产品结果画面吸引注意力。"
      }
    ]
  },
  "structural_slots": [
    {
      "slot_id": "hook_01",
      "role": "hook",
      "start_time": 0.0,
      "end_time": 1.2,
      "duration": 1.2,
      "creative_function": "用强视觉冲击或强痛点制造停留。",
      "information_function": "提出用户痛点或展示最终结果。",
      "required_visual_type": ["产品特写", "人物反应", "结果展示"],
      "required_motion": "快速推进 / 放大 / 手持冲击",
      "shot_size": "close_up",
      "caption_requirement": {
        "need_caption": true,
        "style": "大字报",
        "position": "center_safe_area",
        "semantic_role": "痛点/悬念/利益点"
      },
      "audio_sync": {
        "beat_position": "first_strong_beat",
        "sfx": "impact"
      },
      "transition_out": "whip_pan",
      "importance": "high",
      "copy_risk": "不要复制原视频具体台词和品牌元素，只迁移开头强钩子方法。"
    }
  ],
  "rhythm_curve": [
    {
      "time_range": [0.0, 3.0],
      "pace": "fast",
      "avg_shot_duration": 1.0,
      "purpose": "快速建立吸引力"
    }
  ],
  "caption_style_template": {
    "subtitle_density": "高密度满字",
    "font_style": "粗体大字",
    "keyword_highlight": true,
    "animation": "pop_in"
  },
  "transition_style_template": {
    "main_transition_types": ["whip_pan", "zoom_cut"],
    "usage_rule": "在信息转折或节奏重拍处使用强转场。"
  },
  "packaging_style_template": {
    "stickers": ["箭头", "强调框", "卖点标签"],
    "cover_style": "大字报 + 产品主体特写"
  },
  "transfer_rules": {
    "must_keep": [
      "前3秒必须有高信息密度 hook",
      "镜头切换需跟随 BGM 重拍",
      "字幕承担卖点推进功能"
    ],
    "can_adapt": [
      "具体产品画面",
      "人物动作",
      "场景背景",
      "台词表达方式"
    ],
    "must_not_copy": [
      "原视频水印",
      "原作者 Logo",
      "原品牌素材",
      "原视频独特台词"
    ]
  },
  "confidence": 0.86,
  "risk_notes": []
}
```

## Prompt 修改重点

Reference Analyzer 的 prompt 里建议增加这句话：

> 你不是在复刻样例视频内容，而是在抽象可迁移的创作结构。请将每个镜头/段落转化为 structural slot，描述其创作功能、信息功能、视觉需求、节奏位置、字幕包装、转场和声音卡点要求。

---

# 2. Asset Indexer 修改方案

## 当前问题

Asset Indexer 目前输出：

* content_type；
* tags；
* suggested_usage；
* visual_description；
* confidence；
* usable_segments。

这个结构已经有可用片段概念，但还不够细。

对于真实剪辑，系统必须知道：

* 片段能不能裁成竖屏；
* 主体是否清晰；
* 动作是否完整；
* 运动强度如何；
* 是否适合卡点；
* 是否适合做 hook；
* 是否适合做转场；
* 是否能被复用加工。

## 修改目标

Asset Indexer 要从“素材内容分析师”升级为：

> 素材片段索引器。

它不只是描述整个素材，而是把素材切成多个 candidate segments。

## 推荐输出结构

```json
{
  "schema_version": "1.0",
  "asset_id": "m001.mp4",
  "media_type": "video",
  "duration": 8.4,
  "global_description": "一段室内产品使用场景视频，包含拿起产品、展示细节和实际使用过程。",
  "segments": [
    {
      "segment_id": "m001_s01",
      "start": 0.0,
      "end": 1.6,
      "duration": 1.6,
      "content_type": "产品特写",
      "subjects": ["产品", "手部动作"],
      "action": "手拿起产品并靠近镜头展示",
      "scene": "室内桌面",
      "shot_size": "close_up",
      "camera_motion": "slight_push_in",
      "motion_intensity": 0.45,
      "visual_quality": 0.88,
      "lighting_quality": 0.82,
      "subject_clarity": 0.9,
      "orientation_fit": "9:16_safe",
      "audio_available": false,
      "best_for_roles": ["hook", "develop"],
      "best_for_slot_types": ["产品特写", "结果展示", "卖点强调"],
      "can_reuse_by": ["crop", "speed_up", "zoom_in", "freeze_frame"],
      "risks": ["背景略杂乱"],
      "confidence": 0.87
    }
  ],
  "asset_level_risks": [],
  "confidence": 0.86
}
```

## Prompt 修改重点

建议增加：

> 请不要只描述整个素材。必须将素材拆解为可剪辑片段 segments，每个片段都要判断视觉质量、主体清晰度、竖屏适配性、镜头运动、动作内容、适合承担的结构功能，以及可复用加工方式。

---

# 3. Slot Matcher 修改方案

## 当前问题

Slot Matcher 当前是把每个素材智能分配到结构槽位，并标出 gap。它已经要求 material_id 使用真实文件名，不能编造文件名，这点很重要。

但它目前有两个问题：

第一，它偏“素材中心”。
也就是从素材出发，给素材找槽位。

第二，它的 gap 策略与 Gap Resolver 不一致。
Slot Matcher 提到 `web_search`，但 Gap Resolver 没有这个策略。 

## 修改目标

Slot Matcher 应该从“素材分配器”升级为：

> 结构槽位填充器。

也就是以 structural slot 为中心，为每个 slot 找最合适的素材片段。

## 推荐输出结构

```json
{
  "schema_version": "1.0",
  "template_id": "ref_001",
  "slot_assignments": [
    {
      "slot_id": "hook_01",
      "slot_role": "hook",
      "required_duration": 1.2,
      "selected_candidate": {
        "asset_id": "m001.mp4",
        "segment_id": "m001_s01",
        "source_in": 0.0,
        "source_out": 1.4
      },
      "match_score": 0.87,
      "score_breakdown": {
        "semantic_fit": 0.88,
        "visual_fit": 0.9,
        "duration_fit": 0.82,
        "motion_fit": 0.76,
        "style_fit": 0.8
      },
      "adaptation_plan": {
        "crop": "9:16_center",
        "speed": 1.15,
        "motion": "zoom_in",
        "caption_adjustment": "添加强痛点标题"
      },
      "reason": "该片段主体清晰、视觉冲击较强，适合承担开头 hook 的产品展示功能。",
      "confidence": 0.84
    }
  ],
  "unfilled_slots": [
    {
      "slot_id": "develop_02",
      "need": "人物实际使用产品的过程镜头",
      "missing_reason": "当前素材库中没有人物使用场景，只有产品静态特写。",
      "suggested_gap_strategies": ["reuse", "text_card", "structure_reorder", "ai_generate"]
    }
  ],
  "low_confidence_slots": [
    {
      "slot_id": "cta_01",
      "reason": "有可用素材，但缺少明确行动号召画面。"
    }
  ],
  "confidence": 0.82
}
```

## Prompt 修改重点

建议替换任务描述为：

> 你不是给每个素材找位置，而是为结构模板中的每一个 slot 选择最合适的素材片段。每个 slot 必须有 selected_candidate 或进入 unfilled_slots。匹配时需要综合语义功能、视觉类型、镜头运动、时长适配、字幕/包装需求和节奏位置。

---

# 4. Gap Resolver 修改方案

## 当前问题

Gap Resolver 当前的六级策略方向很好：reuse、static_graphic、text_card、brand_asset、ai_generate、ask_user。

但它目前输出太简单：

```json
{
  "resolved_gaps": [
    {"slot": "develop_02", "strategy": "reuse", "params": {}}
  ]
}
```

问题是 `params` 为空，后续 Edit Planner 不知道具体怎么执行。

## 修改目标

Gap Resolver 要从“策略选择器”升级为：

> 可执行缺口补齐器。

它不仅要说“用 reuse”，还要说明：

* 复用哪个素材；
* 用哪一段；
* 怎么裁剪；
* 怎么变速；
* 加什么文字；
* 是否改变原始结构；
* 风险是什么；
* 是否需要用户确认。

## 新增策略

增加：

```text
structure_reorder
```

因为课题挑战明确提到素材不足时可以通过“结构重排”完成创作。

## 推荐输出结构

```json
{
  "schema_version": "1.0",
  "resolved_gaps": [
    {
      "slot_id": "develop_02",
      "chosen_strategy": "structure_reorder",
      "strategy_priority_level": 5,
      "attempted_strategies": [
        {
          "strategy": "reuse",
          "feasible": false,
          "reason": "现有素材缺少人物使用动作，强行复用会导致语义不成立。"
        },
        {
          "strategy": "text_card",
          "feasible": true,
          "reason": "可以用卖点文字卡替代缺失的使用过程镜头。"
        },
        {
          "strategy": "structure_reorder",
          "feasible": true,
          "reason": "可将原 develop_02 与 develop_03 合并，缩短使用过程展示。"
        }
      ],
      "resolution": {
        "new_slot_type": "text_card_plus_product_closeup",
        "asset_ref": {
          "asset_id": "m003.mp4",
          "segment_id": "m003_s01",
          "source_in": 1.0,
          "source_out": 2.0
        },
        "edit_params": {
          "crop": "9:16_center",
          "speed": 1.0,
          "motion": "ken_burns_zoom_in",
          "overlay_text": "核心卖点一句话",
          "caption_style": "bold_center_title"
        }
      },
      "impact_on_template": {
        "duration_change": -0.5,
        "rhythm_change": "轻微加快",
        "structure_fidelity_loss": "low"
      },
      "requires_human_review": false,
      "confidence": 0.76
    }
  ],
  "still_unresolved": []
}
```

## Prompt 修改重点

建议增加：

> 你的输出必须是可执行补齐方案，而不是抽象建议。每个 gap 必须给出最终 chosen_strategy、具体素材引用或生成内容、编辑参数、对原结构的影响、置信度和是否需要人工确认。

---

# 5. Edit Planner 修改方案

## 当前问题

Edit Planner 当前已经能输出时间线，包括 start、end、slot、asset、source_in、source_out、transform、overlays、transition_out。

但它现在缺少：

* 全局视频参数；
* 多轨道结构；
* 字幕轨；
* 音频轨；
* 包装轨；
* 封面设计；
* 校验结果；
* 人工复核点。

## 修改目标

Edit Planner 要从“时间线生成器”升级为：

> 可执行剪辑方案生成器。

它需要生成更接近剪映工程结构的 EditableTimeline。

## 推荐输出结构

```json
{
  "schema_version": "1.0",
  "timeline_meta": {
    "duration": 16.8,
    "aspect_ratio": "9:16",
    "resolution": "1080x1920",
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
        "crop": "9:16_center",
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
}
```

## Prompt 修改重点

建议增加：

> 你必须生成可执行的多轨时间线，包括视频轨、字幕轨、包装轨、音频/SFX 轨和封面设计。输出前必须进行 validation，检查槽位是否全部填充、素材引用是否真实、时间线是否重叠、source_in/source_out 是否合法，以及结构迁移保真度是否达标。

---

# 五、建议新增第六个 Agent：Verifier / Human Review

## 为什么需要新增

课题强调“更智能、更可控”，所以系统不能只是自动生成。它需要能告诉用户：

* 哪些地方迁移得好；
* 哪些地方因为素材不足而妥协；
* 哪些地方需要人工选择；
* 哪些地方可能存在复刻风险；
* 哪些地方可以进一步增强爆款效果。

## Verifier 输入

```text
Reference Analyzer 输出
Asset Indexer 输出
Slot Matcher 输出
Gap Resolver 输出
Edit Planner 输出
```

## Verifier 输出

```json
{
  "schema_version": "1.0",
  "overall_assessment": {
    "structure_transfer_score": 0.84,
    "material_fit_score": 0.78,
    "rhythm_match_score": 0.81,
    "packaging_match_score": 0.76,
    "originality_score": 0.9
  },
  "strengths": [
    "开头 hook 结构保留较好",
    "整体镜头节奏接近参考视频",
    "字幕承担了卖点推进功能"
  ],
  "risks": [
    "部分 develop 段落由文字卡替代，真实感较弱",
    "缺少人物使用镜头，转化说服力可能下降"
  ],
  "human_edit_suggestions": [
    {
      "priority": "high",
      "slot_id": "develop_02",
      "suggestion": "建议补充一段用户实际使用产品的镜头。"
    },
    {
      "priority": "medium",
      "slot_id": "cta_01",
      "suggestion": "建议强化结尾行动号召字幕。"
    }
  ],
  "pass": true
}
```

## 作用

这个 agent 可以作为最终质量控制模块，也可以作为答辩/汇报里的亮点：

> 系统不仅生成结果，还能解释迁移质量，并给出可控编辑建议。

---

# 六、完整执行流程

## Step 1：样例视频结构抽象

输入：

```text
优质样例视频
```

输出：

```text
structural_slots
rhythm_curve
caption_style_template
transition_style_template
audio_beat_map
transfer_rules
```

核心目标：

> 从样例中学习“结构能力”，不是复制内容。

---

## Step 2：用户素材片段索引

输入：

```text
用户上传的视频 / 图片 / 品牌素材
```

输出：

```text
candidate_segments
```

核心目标：

> 把素材变成可被匹配和剪辑的片段级素材库。

---

## Step 3：槽位匹配

输入：

```text
structural_slots
candidate_segments
```

输出：

```text
slot_assignments
unfilled_slots
low_confidence_slots
```

核心目标：

> 用新素材填入样例视频的创作结构。

---

## Step 4：缺口补齐

输入：

```text
unfilled_slots
candidate_segments
transfer_rules
```

输出：

```text
resolved_gaps
still_unresolved
```

核心目标：

> 当素材不足时，通过复用、结构重排、文字卡、包装、AIGC 或人工补充完成创作。

---

## Step 5：生成可执行时间线

输入：

```text
slot_assignments
resolved_gaps
caption_style_template
transition_style_template
audio_beat_map
```

输出：

```text
EditableTimeline
caption_track
packaging_track
audio_track
cover_design
validation
```

核心目标：

> 生成接近剪映工程的完整视频方案。

---

## Step 6：质量验证与人机协同

输入：

```text
最终时间线
参考结构模板
素材匹配结果
```

输出：

```text
structure_transfer_score
warnings
human_review_points
```

核心目标：

> 保证系统可解释、可控、可修改。

---

# 七、修改优先级

## 第一优先级：必须改

### 1. Reference Analyzer 增加 structural_slots

这是整个系统的核心。如果没有 structural_slots，后面的 Slot Matcher 只能靠模糊语义匹配。

### 2. Asset Indexer 改成 segment-level

不能只分析整个素材，必须拆成可剪辑片段。

### 3. Slot Matcher 改成 slot-centric

从“给素材找槽位”改成“给每个槽位找素材”。

### 4. 统一 slot_id 和 gap strategy

否则后面工程实现很容易出错。

---

## 第二优先级：强烈建议改

### 5. Gap Resolver 输出可执行 params

包括素材引用、source_in、source_out、裁剪、变速、字幕、动效。

### 6. Edit Planner 增加 validation

检查最终时间线是否可渲染。

### 7. 增加 structure_reorder 策略

这个和课题挑战高度对应，建议一定加入。

---

## 第三优先级：作为亮点加入

### 8. 增加 Verifier / Human Review

体现人机协同和可控创作。

### 9. 增加 cover_design

剪映链路里封面很重要，课题背景也提到了封面设计。

### 10. 增加 structure_transfer_score

可以作为系统效果评估指标。

---

# 八、可以写进项目文档的方案表述

你可以这样总结：

> 本项目面向短视频爆款结构迁移任务，设计一套多 Agent 协作的视频创作系统。系统首先通过 Reference Analyzer 对优质样例视频进行结构化拆解，提取其脚本推进、镜头节奏、字幕样式、转场方式、画面包装和 BGM 卡点等创作特征，并将其抽象为可迁移的 structural slots。随后，Asset Indexer 将用户上传素材解析为可剪辑的 candidate segments，Slot Matcher 根据结构槽位需求完成素材适配，Gap Resolver 在素材不足时通过素材复用、结构重排、文字卡、包装补全、AIGC 生成或用户补充等方式解决缺口。最后，Edit Planner 生成包含视频轨、字幕轨、包装轨、音频轨和封面设计的可执行时间线，并通过 Verifier 给出结构迁移质量评估与人工编辑建议。该系统强调迁移优质样例中的创作方法，而非复制具体内容结果，从而支持不同主题、商品和素材条件下的可控短视频创作。

---

# 九、最终你应该怎么改这五个 prompt

## Reference Analyzer

核心改法：

```text
增加 structural_slots、transfer_rules、rhythm_curve、caption_style_template、transition_style_template、audio_beat_map。
```

一句话目标：

> 从样例视频中抽象可迁移的创作结构。

---

## Asset Indexer

核心改法：

```text
从素材级分析改成片段级分析，输出 segments。
```

一句话目标：

> 把用户素材转化为可剪辑、可匹配、可复用的素材片段库。

---

## Slot Matcher

核心改法：

```text
从 material-centric 改成 slot-centric。
```

一句话目标：

> 为每个结构槽位选择最合适的新素材片段。

---

## Gap Resolver

核心改法：

```text
增加 structure_reorder，并输出可执行 edit_params。
```

一句话目标：

> 把素材缺口变成可执行的补齐方案。

---

## Edit Planner

核心改法：

```text
从单一 timeline 改成多轨时间线 + validation + human_review_points。
```

一句话目标：

> 生成可渲染、可检查、可人工调整的完整剪辑方案。

---


