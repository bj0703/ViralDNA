# VisualSupplementSkill / 图生视频补全 Skill

一个统一的图生视频补全 Skill，内部用 mode 区分 5 种不同生成用途。

## 5 种 Mode

| mode | 用途 |
|------|------|
| missing_hook | 补开头强吸引镜头 |
| image_motion | 静态图转轻运动视频 |
| transition_clip | 生成过渡画面 |
| product_motion | 商品图/封面图动态化 |
| slot_fill | 素材不足时兜底填充 slot |

## 调用方式

```python
from visual_supplement_skill import VisualSupplementSkill

skill = VisualSupplementSkill()
result = skill.run({
    "mode": "product_motion",
    "slot": {...},
    "style_context": {...},
    "source_assets": {...},
    "generation_constraints": {...}
})
```

## GapResolverAgent 选择 mode 的逻辑

```python
def choose_visual_supplement_mode(slot, asset_status):
    if slot["role"] == "hook" and asset_status["no_strong_hook"]:
        return "missing_hook"

    if asset_status["has_image_only"]:
        return "image_motion"

    if slot.get("transition_out") in ["blur", "zoom_cut", "whip_pan"] and asset_status["transition_not_smooth"]:
        return "transition_clip"

    if "产品特写" in slot.get("required_visual_type", []) or "商品" in slot.get("required_visual_type", []):
        return "product_motion"

    return "slot_fill"
```
