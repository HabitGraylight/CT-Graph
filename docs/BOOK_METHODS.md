# 从参考书到可验证的知识 / From books to testable knowledge

## 核心方法

长篇书籍采用分层阅读：目录定位 → 按问题检索 → 核对原页 → 写成原子断言 → 检查适用条件与反证 → 转成提示或试验 → 实际试饮验证。全文提取不等于完整阅读；命中关键词不等于证据已核验。

每条证据卡记录来源版本与哈希、PDF 页序、印刷页码、原创概括、证据类型、适用范围、采纳/待审/拒绝决定及对应规则。PDF 页序与印刷页码不可简单混用。扫描页和 OCR 可疑内容保留待审状态。

## 三种互补视角

| 参考 | 可复用的方法 | 在项目中的落实 |
|---|---|---|
| Dave Arnold, Liquid Intelligence | 将剂量、冷却、稀释和测量条件纳入设计 | 出杯状态与酸度测量提示，不采用统一秒数或固定融水率 |
| Alex Day, Nick Fauchald, David Kaplan, Cocktail Codex | 以根型和原料功能组织配方变化 | 六根型导航，与现有评分模板建立多对多编辑映射 |
| Peter Coucquyt, Bernard Lahousse, Johan Langenbick, The Art & Science of Foodpairing | 以香气联系提出候选，同时检查味觉、质地和复杂性 | 搭配假设与试饮任务，不导入商业香气表，不按共有分子加分 |

这些是简短的方法说明，不提供书籍全文、逐章替代摘要或整套搭配表。书内作者的偏好、典型测量值与普遍科学定律分别处理。

### 来源及交叉核验

- [Liquid Intelligence 出版社书目](https://wwnorton.com/books/9780393089035)。酸度提示参考中文版“酸类”印刷页 42–43；书目网页只用于识别作品，段落依据来自实际核读书页。
- [Cocktail Codex 作者团队介绍](https://www.deathandcompanymarket.com/products/cocktail-codex)：六根型是作者的教学体系。项目中的具体模板映射属于编辑推断，不能当作历史谱系。
- [Dave Arnold 的摇和实验](https://www.cookingissues.com/index.html%3Fp=1527.html)：关注温度与稀释，并声明冰初温、冰量、表面带水和搅动条件；实验未评估质地，不能外推成“冰和摇法都不重要”。
- [Ahn 等的风味网络研究](https://arxiv.org/abs/1111.6074)：不同文化菜谱的共有成分模式不同。观察性共现不能证明某个搭配更好喝，也不能识别某次原料替换的因果效果。

## 当前接口

`catalog.design_knowledge` 提供根型、映射边界和版本。评价、补全、改进输出中的 `judge.design_review` 包含条件提示、来源与验证任务，网页同步展示。检查层独立于数值评分，`numeric_score_effect` 全部为空。

当前涉及：原料功能替换、出杯状态缺失、酸度测量、辅酒多重作用、气泡服务、风味搭配假设、目标马天尼版本。没有自动新增真实感官分，没有把六根型当作六个已完成的评分模板。

## 本地书库操作

可选工具需要 Poppler 的 `pdfinfo`、`pdftotext` 在 PATH 中；核心应用不依赖它们。

```sh
python scripts/book_library.py index --folder data/ref_books
python -X utf8 scripts/book_library.py search 稀释 --limit 5
```

仅允许索引项目 data/ 内的 PDF，索引写入 `data/knowledge/library.sqlite`。查询返回本地路径、文件哈希、PDF 页序及有限片段；扫描书单独列出，搜索不到不表示书中没有。繁简体不同或 OCR 错字可能影响检索，必要时更换关键词并回看原页。

原书、文本、截图、索引与详细阅读证据全部本地保留。公开仓库只发布工具、方法与审核后的简短原创规则。核心应用不会自动加载任意阅读笔记成为规则。

## English summary

Use a staged workflow: locate, retrieve, inspect the original page, write an atomic claim, examine conditions and conflicting evidence, then propose a testable rule. Extraction is not reading, and a search hit is not verified evidence.

Keep source hashes, PDF and printed page numbers, evidence type, scope and review decisions locally. Scans remain explicitly unsearchable until visually reviewed or processed with verified OCR. Books and extracted content are never published.

The runtime exposes six root families and conditional design prompts through `catalog.design_knowledge` and `judge.design_review`. These prompts do not change sensory scores. Ingredient similarity generates hypotheses; actual tasting is still needed.


## 工艺进入检查层 / Process-aware checks

现在区分原料投料状态、整杯处理和服务方式。新增条件检查涵盖：粗滤与澄清的区别、澄清后的成分保留边界、加工原料替换、摇和泡沫、批量预调、气泡目标与杯中风味演变。详见 [结构化请求](JUDGE_REQUESTS.md#工艺状态--process-state)。

参考原页：Liquid Intelligence 中文版印刷页 71–72、82–83、213–216、266–268；Cocktail Codex 中文版印刷页 105、249；风味搭配书中文版印刷页 25、35。它们支持条件提示，不提供通用最佳摇和秒数、气泡强度或加工后的浓度。书中数值和作者偏好不自动转成阈值。

Process checks separate ingredient preparation, whole-drink transformation and service. They retain uncertainty about composition, foam and sensory outcomes. There are no fitted causal coefficients or automatic quality bonuses for clarity, small bubbles or complexity.
