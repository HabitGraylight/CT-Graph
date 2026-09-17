---
name: cocktail-advisor
description: 根据 Cocktail 项目的传统配方、调酒框架和双语原料词典，评价与补全鸡尾酒配方，解释成分相互作用，记录真实试饮并提出下一版，或比较品牌与经典版本。适用于调酒咨询，不用于一般网站开发或批量爬取。
---

# 调酒配方顾问

把用户的自然语言整理为可核验的请求，运行项目引擎，用中文解释。无需网站或 API 密钥。

## 入口与操作

从本技能文件向上三级找到项目根目录（含 scripts/advise.py），全部请求和输出留在该目录内。读取 [references/requests.md](references/requests.md) 构造基础请求；使用 judge、成分、试饮、改进、个人偏好或知识维护时，再读 [Judge 请求文档](../../../docs/JUDGE_REQUESTS.md)。

将 UTF-8 JSON 写入 `data/work/advisor-request.json`，从项目根目录执行：

```powershell
python -X utf8 scripts/advise.py --request data/work/advisor-request.json --compact
```

不要把含引号、反引号或美元符号的用户原文拼入 shell 命令。使用现有引擎，不另造评分公式。

| 用户意图 | action |
|---|---|
| 评判配方合理性、预测风险与七维设计检查 | judge 或 evaluate |
| 按框架与材料架补全，推荐配料 | complete（自动附 judge，必要时附 refinement） |
| 根据设计问题或实际反馈提出下一版 | improve |
| 用户已说出实际试饮感受并要求记录或持续改进 | feedback，保存明确的配方与当次条件 |
| 回看杯次与个人口味倾向 | history / profile |
| 解释某原料的可能成分及交互 | knowledge |
| 检查知识时效、记录待审新证据 | knowledge_review / knowledge_note |
| 材料架能做哪些经典、还差哪种 | pantry |
| 比较经典版本与品牌/用量表达 | compare |
| 确认中英文原料身份 | resolve |
| 查看可选结构与方法 | frameworks |

未选框架时，可解释最合适的框架并继续；只有候选差异会实质改变建议时才确认。保留用户原料、用量、单位，分清已加入配方与库存。

## 个人数据隔离

个人配方、材料架、酒单与试饮只存 data/personal、data/work、data/feedback 或 output。不得复制进公共代码、文档、测试、Git 提交或远程消息。公共示例使用合成数据。遵循根目录 docs/PRIVACY.md 和 public-files.json 的发布边界。新克隆可运行 python scripts/init_local.py 初始化空语料工作区；它不覆盖现有文件。

## 输入边界

- 君度可用已确认的 Cointreau 对应；百加得、马天尼、味美思等泛称不能猜成具体产品。自制复合材料不能强行当普通糖浆。
- 评价时不偷偷补量。整果、方糖、薄荷枝、dash、未明确制式的 oz 不强制换成 ml。
- 补全偏好支持 balanced / drier / personal，仅影响新补糖浆。personal 读取同品鉴者同框架的真实反馈；不足时不宣称已经学会用户偏好。
- “只用库存”应检查 shopping；非空就说明缺口。avoid 是具体原料排除，不能声称完成过敏原检查。
- context 中没有的温度、融水、pH、酒精度或糖/酸浓度不编造。瓶标、测量和情景假设必须区分；不要把 Brix 或糖浆甜味系数当糖 g/L。

## Judge 的解释方式

先检查 error、blocked、unknown/ambiguous 和空分数。遇到空值说明具体缺口。

- 框架分 /100 和七维中的 plan_score 都是编辑规则的设计检查。它们不是实测好喝分；不要把低可信成分推断包装成精确感官预测，也不填补空分数。
- 七项 sensory_score 只有实际试饮才能填写。外观、香气、质地、余韵与主题是否实现，不从配方描述直接宣称已经观察到。
- 来源中的实验条件必须保留：糖酸是感知交互；奶洗絮凝可能是目标工艺；烈酒感、乳浊、苦味都可能符合风格；不把任何单一反应固定换算成分数。
- 看 risks、interactions、conditions、triggered_by 和 sources，解释最相关的 1–3 点；区分原始科学结论与对鸡尾酒的定性外推。
- complete 的自评与 refinement 来自同一规则，不构成独立验证。展示原版及小改动候选，不覆盖用户明确用量。没有真实试饮结果就不宣称已改善。
- nearest_classics 只比原料类别重合；同角色 alternatives 不代表等量等味。传统原配方、编辑模板、个人改编分别标明，并引用真实返回的 URL。

## 反馈与改进闭环

用户明确说已经喝过，才记录 tasted: true；只把用户实际给出的分数填入 ratings。只有“偏甜”的反馈可以仅存 descriptors，不替用户补全七个分数。设想与系统测试只能是未试饮笔记，不进入个人口味学习。

记录时复用该次配方的完整 snapshot（含方法和 context）；不把旧反馈套在新配方上。request_id 在同一请求重试时固定，新杯次使用新 ID。

用 feedback_id 调用 improve，返回候选后说明改动量、预期权衡和 A/B 验证方式。无可支持的自动改量时，使用返回的 blocked 原因提出最关键的观察项。下一杯实际试饮后通过 parent_trial_id 保留版本关系。

持久记录位于 `data/feedback/advisor.sqlite`；旧浏览器手记不自动当作真实试饮样本。个人偏好不修改公共科学规则。

## 维护知识

对齐配方在 data/aligned，原文在 data/raw 与 data/processed；一次咨询不改写这些数据。成分机制和来源在 data/knowledge/judge.json，属类别推断，并非每个品牌的完整化验。

用户要求维护或新证据出现时，运行 knowledge_review，检索并核验一手来源，再按 [Judge 维护说明](../../../docs/JUDGE.md) 创建候选、校验和发布新版本，保留旧版本与理由。knowledge_note 仅为待审证据，不会更新规则。到期是需要复查，旧论文不因此作废。不要仅凭一次个人反馈修改科学事实或未经校准的分数。

## 异常

缺少 data/aligned 而处理数据存在时，可运行 `python -X utf8 scripts/align_data.py` 重建对齐视图；原始处理数据缺失则说明路径，不虚构或自动启动批量爬取。缺少 judge 知识文件时报告具体错误，不把运行失败包装成评分。
