# 数据说明与本批采集记录

## 来源

| 来源 | 本批内容 | 质量与复用状态 |
|---|---|---|
| https://opendrinks.io/ / https://github.com/alfg/opendrinks | 756 个饮品配方 | README 明确将贡献配方与内容按 MIT 开放；许可证保存在 `data/raw/opendrinks/files/LICENSE`。社区质量不一 |
| https://github.com/bar-assistant/data | 306 配方、192 原料及杯具技法资料 | 当前下载快照没有找到 LICENSE；虽然搜索索引显示过 MIT，不能据此给当前数据默认授权，标记 unknown |
| https://github.com/teijo/iba-cocktails | 77 个旧版配方 | 当前快照没有许可文件；不是当前官方酒单，保留用于比较 |
| https://iba-world.com/cocktails/all-cocktails/ | 102 个官方配方页面 | 官方配方事实参考；保存为研究快照，未认定整站文字和图片开放授权 |
| https://en.wikisource.org/wiki/The_Bar-tender%27s_Guide | 1887 年版书籍目录、章节和 254 个条目 | 历史作品为公版；站点新增编排和说明遵循页面标注。不是 1862 首版 |
| https://en.wikipedia.org/ | 67 个背景词条 | CC BY-SA；保留 URL、修订链接和原文引用标记。属于二手资料，不能直接当作起源定论 |

当前 SQLite / JSONL 是混合研究语料，不是统一 MIT 许可的可直接发布内容包。站点上线时应按来源选择可复用字段、保留归属，并为受保护叙述重新撰写内容。仓库原始 ZIP 可能自带媒体文件；未提取媒体到内容层，也未授予图片使用权。

## 原始层

原始网页保留 HTML；仓库保留下载 ZIP 与 JSON/说明文本。每次下载旁边都有 `.meta.json`：URL、最终 URL、UTC 时间、HTTP 状态、SHA-256、字节数、ETag、Last-Modified（服务端有提供时）。

仓库快照的 Git commit（取自 GitHub ZIP 注释）：

- Bar Assistant：`73bbd3651670b7556550ae9e37552c8737eb777e`
- IBA community：`5f1e5dd4a2189adc3854a51d7b48640bd86e9f76`
- Open Drinks：`f446f0e9356b9b43155d207b4f7c5214d9da91ab`

`sources.jsonl` 中仓库文件 URL 指向分支便于浏览；严格复现以本地 ZIP、上述 commit 和 SHA-256 为准。处理过程不覆盖原始文件。

## 配方模型

- `id`：来源内配方版本的稳定 ID。
- `name`：原始名称。图谱中的 `drink_name` 只是名称分组，不代表已完成实体消歧。
- `dataset` / `source_id`：来源层级。
- `ingredients[]`：`name`、`amount_raw`、`unit_raw`、`amount_numeric`、`amount_ml`、`raw`。
- `instructions`：字符串或步骤数组，保留上游结构；消费者需兼容两者。
- `garnish` / `glass` / `method` / `tags`：仅存在时保留，缺失不猜测。
- `source_abv_unverified`：上游配方估算酒精度，不用于精确成品度数；不同品牌和融冰量会影响结果。
- `upstream_source`：社区数据引用的第三方出处，只是来源提供的链接，不表示本批已访问验证。

只将明确的 ml、cl、l 换算为 ml。oz 不擅自判断美制或英制；dash、drop、bar spoon、cup、历史 wine-glass / pony-glass 等保留原单位。分数可以解析为数值，但不改变单位含义；范围和不明确措辞保持原文。

IBA 中 50 行尚未可靠拆分，使用 `HAS_UNPARSED_INGREDIENT` 指向 `ingredient_expression`；不会把它们当作已确认的原料实体。Open Drinks 仍有混在单位/名称中的自由文本，待第二轮语义清洗。

## 文献与历史

`documents.jsonl` 保留处理后的正文，原始 HTML 可用于检查参考文献。`history_evidence.jsonl` 只抽取匹配历史/起源相关章节的段落组，因此不能表示历史内容已全部覆盖。所有历史证据标记为二手来源待核验；没有用模型编造缺失的日期、发明人或地点。

公版书条目保留原始用量和制作方法文本，尚未自动拆成现代配方结构。一个条目可能包含多个变体或一般制作说明，254 指条目页数量，不是严格配方数量。古配方不应未经现代适用性审查直接作为饮用操作建议。

图谱中的 `ATTRIBUTED_TO_AUTHOR` 表示书籍作者，不表示该作者发明了条目中每种饮品。`HAS_BACKGROUND_ARTICLE` 是标题匹配的待复核链接。`HAS_SOURCE_ORIGIN_LABEL` 是来源提供的原料产地标签，不是鸡尾酒发明地点。

## 图谱关系

- 名称 → `HAS_RECIPE_VERSION` → 配方版本。
- 配方 → `USES_INGREDIENT` → 原料，边上保留用量和顺序。
- 配方 → `SERVED_IN` / `USES_METHOD` / `HAS_SOURCE_TAG` → 杯型 / 技法 / 来源标签。
- 原料 → `HAS_RECIPE_SPECIFIC_SUBSTITUTE` → 替代原料，边上保留适用配方 ID；不扩展为通用可替代关系。
- 原料 → `IN_SOURCE_CATEGORY` → 来源分类。
- 名称 → `HAS_HISTORICAL_ENTRY` / `HAS_BACKGROUND_ARTICLE` → 文献。
- 文献 → `IN_BOOK` / `ATTRIBUTED_TO_AUTHOR` → 书籍 / 作者。
- 各记录 → `SOURCED_FROM` → 来源。

每条关系都有 `source_id`。1,770 个原料标签尚未完成近义词合并，658 个标签也混合口味、场景、类别和自由关键词；不可把它们当作已清洗的本体。

## 已知质量问题

- 72 行未提供独立原料名；原始结构保留在 `raw`，常见于自由文本或原料被放进单位字段。
- 50 行 IBA 用量表达尚未自动拆分。
- 1 个旧社区配方（Barracuda）没有步骤；其他来源版本独立保存，不回填伪装成该来源原文。
- 121 组同名配方候选：没有删除来源版本，也没有把同名直接判为相同配方。
- 原料品牌、甜干分类、拼写、杯型同义词和跨语言名称尚未完全对齐。
- 主要语料是英文；没有批量生成未经审核的中文内容。

## 采集异常

最初 GitHub API 因共享出口配额返回 403，改用公开 ZIP 下载；未使用认证或绕过权限。Bar Assistant 的 `master` 压缩包返回 404，实际数据从 `main` 获取。`Don_Beach` 返回 404，已修正为 `Donn_Beach` 并成功获取，旧失败记录保留在 `data/collection_errors.json` 作为日志。书籍和 IBA 配方采集错误日志均为空。

## 验证边界

`scripts/validate.py` 检查数据结构、出处、哈希、公制换算、官方配方解析和本地检索。它不验证所有历史事实、味觉标签或配方可口程度，也不判断网站内容的最终复用权限。
