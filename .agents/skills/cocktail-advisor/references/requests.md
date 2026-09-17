# 本地请求接口

从项目根目录运行 `python -X utf8 scripts/advise.py --request <项目内的 JSON 文件> --compact`。成功退出码 0；非法输入退出码 1 并输出 `error`。业务上需要确认的情况可以退出 0 且 `blocked: true`，因此仍须查看 JSON。

## 字段

- `action`：必填。基础操作 evaluate / complete / compare / pantry / resolve / frameworks / catalog。新增 judge、improve、feedback、history、profile、knowledge、knowledge_review、knowledge_note 见 [Judge 请求文档](../../../../docs/JUDGE_REQUESTS.md)。
- `frame`：需要评价或补全时明确填写；CLI 默认 sour，不应无解释地依赖默认值。
- `recipe`：简短文字或列表。列表项为 `{"name":"金酒","amount":45,"unit":"ml"}`；未提供用量时用 null。
- `pantry`：库存名称文字或同结构列表。当前只按有无，不核算余量。
- `avoid`：补全排除项，同样可用文字或列表；未知/歧义名称需要先确认。
- `method`：shake / stir / build / shake_top。未提供可省略。
- `preference`：balanced / drier / personal；只影响新补糖浆，不覆盖原有用量。
- `name`：compare 使用的鸡尾酒名称。

以上为基础操作字段；context、tasting、feedback_id 等新增字段及适用操作见 Judge 请求文档。未支持字段会报错。可先用 `frameworks` 获取框架定义；`catalog` 还会返回完整词典和比较组，较长，仅需要时读取。

## 框架 ID

sour、daisy、old_fashioned、martini、manhattan、negroni、highball、collins、spritz、mule、julep、tropical。定义与支持角色以运行时返回为准。

## 评价示例

用户：“按酸酒框架看看，金酒 45 毫升，柠檬汁 60，糖浆 5，都是毫升，摇和。”

用户已明确说明“都是毫升”，因此可以传入：

```json
{
  "action": "evaluate",
  "frame": "sour",
  "recipe": [
    {"name": "金酒", "amount": 45, "unit": "ml"},
    {"name": "柠檬汁", "amount": 60, "unit": "ml"},
    {"name": "原味糖浆", "amount": 5, "unit": "ml"}
  ],
  "method": "shake"
}
```

解读 `checks` 中每个槽位的 state 和 `suggestions`，不要只复述总分。用户未明确单位时不能照此补上。

## 补全示例

用户：“选尼格罗尼，已经确定金酒 30 ml，我有金巴利和马天尼红。”

```json
{
  "action": "complete",
  "frame": "negroni",
  "recipe": [{"name": "金酒", "amount": 30, "unit": "ml"}],
  "pantry": ["金巴利", "马天尼红"],
  "preference": "balanced"
}
```

检查 `recipe[].origin`：kept 保留；quantity_completed 补量；pantry 使用已有；shopping 待补充。
若只写“马天尼”，应保留歧义，不替用户选红味美思。

## 排除与库存限制

```json
{
  "action": "complete",
  "frame": "tropical",
  "recipe": [],
  "pantry": ["陈年朗姆酒", "青柠汁", "君度", "原味糖浆"],
  "avoid": ["杏仁糖浆"]
}
```

排除原料不等于排除某种过敏原。用户要求“不添购”时，仅把无购物项且没有未确认核心材料的结果称为可按库存完成；否则解释结构上缺少什么。

## 查品牌、版本与库存

```json
{"action":"resolve","recipe":["君度","Cointreau","马天尼","阿佩罗"]}
```

```json
{"action":"compare","name":"尼格罗尼"}
```

```json
{"action":"pantry","pantry":["金酒","君度","青柠汁"]}
```

`compare` 保留原文与来源，其结果不受 `--compact` 裁剪，以免丢失差异证据。结果过长时用 Python 读取 JSON 并挑选用户关心的版本/字段，不截断后猜剩余内容。
