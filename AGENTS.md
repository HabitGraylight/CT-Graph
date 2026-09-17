# Cocktail 项目协作

所有项目代码、数据、请求文件和生成结果放在本项目目录内。

当用户要求按框架评价或补全鸡尾酒配方、根据手边原料推荐、确认中英文品牌对应、比较传统配方版本时，读取并使用 [.agents/skills/cocktail-advisor/SKILL.md](.agents/skills/cocktail-advisor/SKILL.md)。直接调用本地引擎即可，不需要先运行网站。

普通网站开发、数据采集和代码修改任务不必加载该建议 skill。原始数据 `data/raw/` 与 `data/processed/` 不因一次配方咨询而改写；对齐视图位于 `data/aligned/`。

## GitHub 发布与隐私

仓库只发布 public-files.json 中审核过的方法、代码、文档和合成示例。data/、output/、tmp/、私人配方、酒单、库存、试饮、请求与生成物全部保留本地，禁止写入提交、历史、Issue、PR 或日志。公共代码与测试中也不能复制个人内容。新增文件默认不发布，提交和推送前运行 scripts/check_publication.py，并人工检查差异；不能用 git add -f 绕过隔离。参见 docs/PRIVACY.md。

## 参考书与知识吸收

书库位于本地 data/ 内，使用 scripts/book_library.py 按 PDF 页检索；扫描件需视觉核对。已有本地阅读记录在 data/knowledge/books/READING_REPORT.md 与 reviewed_claims.json。区分全文提取、定向阅读与已审断言，不宣称已通读。来源页序、版本哈希、条件与采纳决定本地保留；公开方法见 docs/BOOK_METHODS.md。个人阅读笔记不得自动提升为公共规则。
