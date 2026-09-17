# 参与贡献 / Contributing

欢迎缺陷修复、知识来源核对和可解释的模型改进。先阅读 README 和 docs/PRIVACY.md。

## 提交前 / Before a pull request

1. 从干净克隆运行 `python scripts/init_local.py`。不要复制维护者的 data/。
2. 使用合成的最小复现；不要在 Issue、PR、截图或日志中放入私人酒单和书籍内容。
3. 知识改动写明来源、适用条件、反例及验证方法。区分作者观点、实验结果和项目推断。
4. 运行测试与 `python scripts/check_publication.py`。新增公开文件需明确加入 public-files.json，并在 .gitignore 中加入精确允许项。
5. 提交可独立审查的小改动，说明行为变化和验证；中英文首页同步更新。

Use a clean installation and synthetic examples. Never include personal recipes, books, extracted passages or private logs in an issue or pull request. Knowledge changes need evidence, conditions and a validation plan. Add each new public file to the explicit manifest and ignore-rule exceptions; run tests and the publication checker.

## 沟通 / Communication

讨论具体行为与证据，尊重不同经验和口味。不要把个人喜好包装为通用科学定律。隐私或凭据泄漏请使用 GitHub 私密漏洞报告入口（若已启用），不要把敏感内容贴到公开 Issue。

Discuss evidence and behavior respectfully. Personal taste is not a universal law. Do not post sensitive material publicly; use GitHub's private vulnerability reporting if enabled.

## 许可待定 / License pending

项目所有者稍后决定许可证。当前不使用 CLA，不自行选择或添加许可；提交前确保你有权贡献相关内容，不引入第三方全文或受限数据库。

The owner will choose the license later. Do not introduce a license, CLA, third-party full text or restricted databases without an explicit project decision.
