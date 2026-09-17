# Judge 与反馈接口

将 UTF-8 JSON 写入项目内，再运行：

```powershell
python -X utf8 scripts/advise.py --request data/work/advisor-request.json --compact
```

这些动作也可以由项目 skill 使用。`evaluate` 与 `judge` 同时返回原有框架判断和 `judge`。`complete` 自动带 judge 及必要时的 `refinement`。`improve` 仅输出候选，未自动应用或写入真实试饮记录。

## 设计评价

```json
{
  "action": "judge",
  "frame": "sour",
  "recipe": "金酒 45ml, 柠檬汁 25ml, 原味糖浆 20ml, 牛奶 15ml",
  "method": "shake",
  "context": {"intent": "original", "appearance_target": "clear", "theme": "柑橘奶香"}
}
```

`context` 可选字段：

| 字段 | 可用值 |
|---|---|
| intent | classic / original / milk_clarified |
| appearance_target | clear / cloudy / foam / any |
| texture_target | silky / light / foamy / sparkling / any，作为意图保存，未做自动达标评分 |
| theme、garnish | 不超过 1000 字的目标/装饰描述，保存并用于讨论，不能当作已实现 |
| glass_chilled | true / false，用户报告的操作记录，不自动实测评分 |
| dilution_ml | 额外融冰/水量 0–5000 ml；未知省略 |
| temperature_c | -30–100 ℃；未知省略，记录值不等于符合统一温度标准 |
| final_ph | 0–14，记录最终测量 pH；不由果汁体积推算 |
| composition | 见下例；字段需先通过名称对齐 |

## 带明确假设的浓度估算

**以下数字是演示情景，不是对这些原料的检测结果。** 使用时替换为用户真实瓶标或测量，并说明测量方法。`abv` 使用百分数，例如 40；`sugar_g_l` 为糖 g/L；`acid_g_l` 为以柠檬酸计的可滴定酸度 g/L。不要把 °Brix 直接当作复杂含酒精液体中的糖浓度。

```json
{
  "action": "judge", "frame": "sour", "method": "shake",
  "recipe": "gin 45ml, lemon_juice 25ml, simple_syrup 20ml",
  "context": {
    "dilution_ml": 20,
    "composition": [
      {"name":"gin","abv":40,"sugar_g_l":0,"acid_g_l":0,"basis":"assumption","source":"演示假设，非瓶标"},
      {"name":"lemon_juice","abv":0,"sugar_g_l":20,"acid_g_l":50,"basis":"assumption","source":"演示假设，非实测"},
      {"name":"simple_syrup","abv":0,"sugar_g_l":600,"acid_g_l":0,"basis":"assumption","source":"演示假设，非实测"}
    ]
  }
}
```

每条至少一项数值；`basis` 为 label / measurement / assumption，`source` 必填。同一原料多条不同成分数据不允许，批次不同须先拆出明确身份。未给的数值不默认 0。

## 保存真实试饮

仅当用户说已经实际品饮，才填 `tasted: true`。配方和条件必须是该次实际做的版本。`request_id` 为本次记录固定 ID，重试沿用；新的杯次使用新 ID。不把下列演示分数写入用户资料。

```json
{
  "action": "feedback", "frame": "sour", "method": "shake",
  "recipe": "金酒 45ml, 柠檬汁 25ml, 原味糖浆 20ml",
  "request_id": "replace-with-real-trial-id",
  "tasting": {
    "tasted": true,
    "ratings": {"appearance":8,"aroma":7,"balance":6,"structure":7,"texture":7,"execution":8,"expression":7},
    "overall_liking": 6,
    "descriptors": ["too_sweet"],
    "notes": "这里填写用户实际反馈，而非复制示例",
    "taster": "local"
  }
}
```

维度字段：appearance、aroma、balance、structure、texture、execution、expression。每项 0–10，可只填用户明确给出的部分；未给不猜，只有七项全填才汇总 /70。总体喜欢 `overall_liking` 独立记录。

描述标签：too_sweet 偏甜，too_sour 偏酸，too_bitter 偏苦，too_strong 刺激突兀，watery 水感过重，flat 气泡不足，aroma_weak 香气弱，astringent 过涩，foam_unstable 泡沫不稳，balanced 合意。可以仅记录文字，系统不能从自由文字偷偷生成分数。

未实际品饮可保存 `{"tasted":false,"notes":"设计想法"}`，不能同时填写感官分；此记录不参与口味学习。更正同一次试饮时，在新的 feedback 请求中填 supersedes_trial_id 指向原记录，提供更正后的完整配方、条件及 tasting。旧记录会退出偏好统计；可以改为 tasted: false 撤回误报。更正不会算成新增杯次。已更正记录不能再次被替代，应指向其最新更正版本。

## 改进与下一杯

```json
{"action":"improve","feedback_id":"实际返回的反馈ID"}
```

系统从反馈读取原配方、方法与条件；若同时传入这些字段，必须匹配记录。无反馈也可以按设计问题生成候选：

```json
{"action":"improve","frame":"sour","recipe":"金酒 45ml, 柠檬汁 60ml, 原味糖浆 5ml","method":"shake"}
```

返回 `blocked` 时解释需要观察什么，不能编出改进版。候选 `candidate` 含 frame、recipe、method、context，可用于下一杯；实际试饮后保存 `feedback`，并填 `parent_trial_id` 连接上一条试饮。

```json
{"action":"history"}
```

返回项目中的试饮与待审证据记录。`profile` 可用 `frame`、`taster` 筛选。`complete` 的 `preference: personal` 根据该品鉴者在同框架的真实历史选择是否减少新补糖浆，输入量仍保留。

## 查询、复核知识

```json
{"action":"knowledge","name":"牛奶"}
```

查看类别成分与可能参与的机制；`potential_interactions` 只说明相关，不代表给定配方已经满足所有触发条件。

```json
{"action":"knowledge_review"}
```

```json
{"action":"knowledge_note","rule_id":"foam_lipid","url":"https://实际一手来源地址","finding":"核实后填写：哪条结论、实验基质与限制发生变化"}
```

`knowledge_note` 只是待审证据。维护知识版本的审核发布步骤见 [JUDGE.md](JUDGE.md)。


## 工艺状态 / Process state

可选 `context.process` 参与评价、补全、改进和试饮快照。省略代表未知。

```json
{
  "action": "judge",
  "frame": "sour",
  "recipe": "gin 45ml, lemon juice 25ml, simple syrup 20ml",
  "method": "shake",
  "context": {
    "process": {
      "clarification": "strained",
      "carbonation": "none",
      "service": "up",
      "batched": true,
      "preparations": [{"name": "lemon juice", "state": "clarified"}]
    }
  }
}
```

- `clarification`：`none` 无整杯澄清、`strained` 仅滤冰/粗果肉、`whole_drink` 整杯澄清。预先澄清的一种原料记在 preparations，不要记成整杯澄清。
- `carbonation`：`none`、`top_up` 后加气泡料、`force` 整杯充气。它只说明方案，不证明已达到某个 CO₂ 浓度，不提供设备压力指令。
- `service`：`up` 无冰出杯、`on_ice` 杯中留冰；`batched` 必须为布尔值。
- `preparations`：最多 80 项，每项为配方中已识别且不重复的 name 和当前 state（`fresh`、`heated`、`infused`、`fermented`、`clarified`）。这是投料状态标签，不是完整工艺序列；多步过程尚需另行记录。

composition 数值必须对应实际投料状态，不能把鲜汁数值冒充加工后实测。整杯澄清或兼容字段 `intent: milk_clarified` 会将 `composition.estimates` 标为工艺后未知；原来的混合情景存入 `input_scenario_estimates`，包括已声明额外水量。出液量不能单独确定溶质保留率。未声明整杯转化时，原浓度计算仍是近似情景，不能当作实测。

整杯澄清的无反馈自动改进会暂停，要求真实试饮；有反馈时仍只产生单变量候选，不预测味觉收益。网页支持整杯处理、气泡、服务与预调选择；具体原料状态可通过 JSON 提供，并随载入快照保留。

**English:** `context.process` records preparation and service conditions without inventing sensory scores. Whole-drink clarification invalidates final concentration estimates; the input scenario remains separately available. Ingredient-level preparation describes the material actually dosed, not a processing sequence. Missing fields mean unknown. Recipe-only auto-tuning is blocked after unmodeled whole-drink clarification; real tasting can support a controlled trial.
