# Changelog / 更新记录

## 2026-10-06 · Domain graph V2 and Sour experiments

- Stable domain projections: ingredient uses, unresolved identity, declared product variants/batches, composition records, conditional claims and source provenance.
- Ordered process states; step-aware carbonated shaking checks, water accounting and clarification uncertainty. Completion preserves ingredient references when grouping rows.
- Three Sour candidates with concentration tradeoffs, evidence links and bounded personal ordering.
- Append-only local A/B plans, randomized presentation, timepoint observations, intensity/quality/liking separation, correction handling and retry-safe records across knowledge updates.
- Recipe Lab UI, material/composition inputs, local trial history, CLI/API and updated advisor skill.
- No fitted causal effects, no fabricated sensory scores, no redistribution of books, reference corpus or personal data. License remains pending.

## 2026-09-17

### Added

- 工艺与服务状态检查：整杯澄清后的成品浓度保持未知；单独追溯投料情景，阻止缺少实饮依据的比例自动修正。
- 原料加工、批量摇和质地与气泡目标提示；网页补充工艺选项。

- 中文默认首页与英文介绍、原创项目横幅、贡献指南和路线图。
- 空数据 CI 与发布清单检查；双语 Issue 和 PR 模板。
- 本地 PDF 逐页检索工具：文件哈希、PDF 页码与扫描件识别。
- 六根型知识导航和带条件的设计复核：替换、稀释、酸度、辅酒、气泡、搭配假设及目标版本。

### Boundaries

- 未上传书籍、原文提取、个人配方、试饮或阅读笔记。
- 未更改原有评分公式，未拟合感官或因果预测模型。
- 许可证待定。

## Initial publication

Reusable advisor, Judge, framework vocabulary, local workbench and synthetic tests, with an explicit public-file manifest. Personal and collected data excluded.
