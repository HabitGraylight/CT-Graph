# Judge 验收记录

日期：2026-09-15。知识版本：2026-09-15.1。

## 自动检查

- `python -X utf8 -m unittest discover -s tests -q`：46 项通过。
- `python -X utf8 scripts/validate.py`：数据 ID、来源 hash、图谱关系、单位转换、IBA 覆盖及 SQLite 检查全部通过；原始来源内容未改写。
- `node --check web/app.js`、`node --check web/judge.js`：通过。
- `quick_validate.py .agents/skills/cocktail-advisor`：通过。
- `scripts/review_knowledge.py --candidate data/knowledge/judge.json --check`：13 来源、14 成分类型、127 档案、11 机制通过结构与引用校验。

关键行为测试包括：未观察维度留空、牛乳与椰奶区分、奶洗意图、气泡料单独加入、浓度缺失不默认 0、明确假设的 ABV/糖酸计算、反馈并发幂等、知识更新后重试、七项全填才汇总、更正记录退出偏好统计、按人和框架隔离、偏好只影响新补用量、修订保留原版及排除约束、待审证据不自动发布、知识发布保留旧版与审计记录。

反馈与发布测试使用项目 `data/work` 内的临时目录，未向用户的真实口味历史写入模拟试饮。

## 网页交互验收

在本地网页检查了：

1. 七维设计复核正确呈现；香气、外观等无观察时不编分。
2. 偏酸示例产生单变量候选，并展示改前改后及仍存在的问题。
3. 试饮反馈表初始未选“已试饮”，感官分数输入禁用。
4. 「成分与依据」显示原料档案、机制、来源与复核日期。

保存反馈 → 项目历史 → 根据该记录改进的 HTTP 全流程，在隔离数据目录中验证。

示例机器输出位于 `data/work/judge-judge-example.json`、`data/work/judge-refinement-example.json`、`data/work/judge-review-example.json`；均为设计示例，没有实际试饮断言。

## 当前限制

没有真实盲测数据，因此没有训练或宣称校准过“好喝概率/分数”。127 个档案是类别定性知识，并非品牌化验。知识更新通过来源复核和版本发布；未建立后台论文监控。网页支持新增试饮，对既有记录的更正目前通过 skill/API 完成。
