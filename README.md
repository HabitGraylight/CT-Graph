# CT-Graph

可在本地运行的鸡尾酒知识方法与配方建议工具：调酒框架、双语原料与品牌消歧、七维 Judge、成分交互解释、试饮反馈和因果图设计。

**本仓库发布方法与可复用代码。个人配方、材料架、酒单、菜单文件和试饮数据全部保留本地。** 详见 [数据隔离规则](docs/PRIVACY.md)。不附带采集网页或完整第三方配方数据库。

## 快速开始

需要 Python 3.10+。在克隆后的仓库根目录执行：

```sh
python -m pip install -r requirements.txt
python scripts/init_local.py
python server.py --port 8765
```

打开 http://127.0.0.1:8765 。初始化不联网、不覆盖已有本地数据。

不下载语料即可使用 12 个框架、127 个原料与品牌条目，进行评分、补全、定性成分检查及本地试饮记录。经典版本比较与库存匹配需要另外建立来源语料；空语料状态不返回虚构的经典配方。

也可以通过 [cocktail-advisor 技能](.agents/skills/cocktail-advisor/SKILL.md) 调用 CLI：将请求放入 `data/work/request.json`，运行：

```sh
python -X utf8 scripts/advise.py --request data/work/request.json --compact
```

[请求格式和合成示例](docs/JUDGE_REQUESTS.md) · [建议引擎说明](docs/ADVISOR.md)

## 判断边界

- 框架分与设计检查是编辑规则，不是实测好喝分。七维感官分只能来自真实试饮。
- 成分档案属于类别层面的定性推断，不是逐瓶化验；机制有来源、适用条件和复查信息。
- 推荐与自评使用同一套规则，自评提升不能代替独立试饮验证。
- [因果图方案](docs/GRAPH_V2_DESIGN.md) 及 `examples/sour_syrup_dose.draft.json` 是未拟合的研究草案，不宣称已识别因果效应。

## 可选：建立本地来源语料

先阅读 [数据来源与边界](docs/DATA_NOTES.md)，确认来源条款和采集范围，再依次运行：

```sh
python scripts/collect.py
python scripts/collect_pages.py
python scripts/collect_book.py
python scripts/collect_iba.py
python scripts/build_data.py
python scripts/validate.py
python scripts/align_data.py
```

采集需要网络，可能受到源站变化和访问限制影响。所有原文、处理结果和对齐视图保存在忽略的 `data/` 下。文档中的语料数量是早期本地快照记录，不代表仓库包含这些数据。不要将其上传到本仓库。

## 测试与发布

```sh
python -X utf8 -m unittest discover -s tests -q
python scripts/check_publication.py
```

测试使用合成请求；三项语料集成测试仅在本地存在对应语料时运行。发布检查需在 Git 仓库内执行，并检查暂存区和历史路径。逐文件发布清单是 `public-files.json`，新文件默认不发布。

[Judge 与知识维护](docs/JUDGE.md) · [数据隔离与发布规则](docs/PRIVACY.md)

目前未指定代码开源许可证。第三方来源的权利与使用条款独立于本项目。
