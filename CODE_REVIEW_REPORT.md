# CrossRepro self-review report

## 2026-09-18 当前审查与修复

审查对象：交付包内源码、协议、测试、示例和 CI；依据 `plans/` 的 v0.1 范围与验收要求。
当前目录已初始化为本地 Git `main` 分支，但没有提交或远端；本轮仍通过原始 ZIP
和 SHA-256 清单核对变更。该状态不等于已经发布或触发 CI。
这是主任务审查与复核，不冒称独立第三方审计。

结论：**本地修复与 Windows 验收完成；正式发布门槛未完成**。详见 `VALIDATION_REPORT.md` 当前版本章节。

| 优先级 | 原问题 / 触发条件 | 本轮处理与验证 |
|---|---|---|
| P1 | `capture/runner.py:shell_argv` 的 PowerShell `-Command` 将示例退出码 3/2 变成 1，导致错误 verdict | 编码传递脚本并保留原生命令退出码；两个 PowerShell 版本和真实示例验证 |
| P1 | `replay/runner.py`、`cli.py:replay` 将原始命令和 setup 失败命令写入报告 | 统一脱敏结构化报告与失败原因，假密钥回归通过 |
| P1 | `bundle/builder.py:safety_scan` 跳过扩展名/解码失败，但 ZIP 仍收录对应文件 | 扫描所有收录文本、拒绝不可扫描内容和链接，用同一字节快照生成 ZIP/manifest/SHA256 |
| P1 | `cli.py:_reset_state_dir` 对标记目录递归删除，可能丢掉后来加入的文件 | 只清理已知生成文件，未知内容与链接拒绝；保护当前目录及祖先 |
| P1 | `ci/github.py` 直接拼接复现路径进 Shell | 路径作为环境数据传参，拒绝 GitHub 表达式和已检测凭据；本机执行生成的 Replay/Summary 命令 |
| P2 | `redact/patterns.py` 未覆盖 Cookie、Basic Authorization、转义的 Windows 用户路径和 JSON 密钥赋值 | 补充模式及结构化序列化前脱敏，固定假数据验证 |
| P2 | 已脱敏输出用于 signature 匹配，包含邮件/密钥的特征会改变判定 | 原始输出仅保留内存用于比较，报告使用脱敏内容与编号 checks |
| P2 | pack 只验证 repro 文件存在；Schema 允许布尔版本、Windows 驱动相对路径、未知/重复字段 | 打包前做完整校验，拒绝歧义和越界路径，补回归 |
| P2 | Windows 输出解码线程异常；启动权限错误未归入 blocked | 按字节采集后解码，启动失败转为环境阻塞；相关实际/模拟用例通过 |
| P2 | Git 状态整体 strip 丢失首条状态空格，文件名与重命名解析不完整 | 使用 NUL 分隔 porcelain，保留空格与目标路径，单元回归通过 |
| P2 | README 参数与实现不一致；CI 缺少 Summary、真实示例闭环和安装验证 | 文档使用 `--base-dir`；完善三平台六任务矩阵及 artifact 检查 |

初始新增 18 项回归已在修改前执行并全部失败；最终全套 **111 通过、1 跳过**。
跳过项是当前主机无法创建真实符号链接；未以 mock 或静态检查代替该环境验证。
基线、失败记录、最终日志及差异位于 `../build_artifacts/`。

范围限制：没有真实托管三平台执行证据，没有本轮 Linux/macOS 验证；没有外部使用、正式发布或申请提交。
文本模式无法证明所有秘密格式都被发现；v0.1 不提供恶意命令沙箱、任意二进制扫描或并发文件系统事务。
这些边界已写入 `docs/privacy.md` 和 `docs/repro-schema.md`。

原有 hashing/manifest 的目录接口为兼容保留，未开展无关删除或架构重写。新的快照构建仍分别复用这两个模块。

## 以下为原始交付的历史审查记录

## Reviewed areas

- CLI safety and error handling
- subprocess execution boundaries
- output-directory deletion safety
- environment data minimization
- secret/PII redaction
- schema type/semantic validation
- path traversal protection
- replay/blocked semantics
- deterministic verdict logic
- bundle composition/integrity
- generated GitHub Actions structure
- packaging metadata
- test coverage

## Architecture conclusion

The v0.1 core is intentionally small and separated into modules:

```text
capture -> redact -> schema -> replay -> verdict -> bundle/ci
```

`cli.py` orchestrates those modules rather than owning their business logic.
The deterministic verdict engine has no LLM dependency.

## Third-party provenance

This snapshot does not vendor source from Devtriage,
`support-to-repro-pack`, or `codex-windows-doctor`. Their public projects
informed earlier product research, but the delivered baseline code was written
against CrossRepro's own interfaces. `THIRD_PARTY_NOTICES.md` and `licenses/`
record this boundary and the observed MIT license texts.

If upstream source is copied later, exact provenance and license notices must be
added before release.

## Known intentional limitations

- `repro.yml` v1 supports command-level reproduction only.
- no Docker/VM sandbox yet;
- no GUI/browser reproduction;
- no network capture;
- no LLM-based verdict;
- a portable bundle does not snapshot an arbitrary source tree: recipients
  still need the relevant source checkout/files required by the command;
- pattern-based redaction cannot prove that every possible secret format is
  detected, so human review remains required before public sharing;
- automatic `collect` signatures are intentionally conservative and are only
  generated for a non-zero exit code when the command itself required no
  redaction.

## Release recommendation

Use this delivery as the baseline commit for the real repository, then run the
platform work in `CODEX_NEXT_STEPS.md`. Do not call it final `v0.1.0` until
Windows/macOS/GitHub Actions validation is green.
