# Data-aware 最小实验：BLOCKED

日期：2026-09-23。结论：**输入条件未满足，暂停于缓存／来源恢复门槛**。
缓存定位用时 8 分 34 秒，未找到两套历史 `residual_nlist1024` 面板或可恢复它们的原变换状态；无需耗满 30 分钟再停止。没有运行量化实验，也没有产生或估填 48 行 SSE。

## 环境与隔离

- 主机：`rwcpu8.cse.ust.hk`，24 个可见 CPU；开始时约 26 GiB 可用内存，持久卷约 815 GiB 空余。
- 原仓库：`/rwproject/kdd-db/kluaq/archive/projects/ann/saq`；`/rwproject/kdd-db/kluaq/saq` 是兼容链接。
- 原分支：`backup/codex-config-20260718`，提交 `4695de2`。原有未跟踪目录 `docs/sources/`、`results/caq_co0_v2_b1_registered_2da5e9f/` 原样保留，未读其中研究数据。
- 独立分支：`data-aware-minimal-20260923`；worktree：`/rwproject/kdd-db/kluaq/worktrees/saq-data-aware-minimal-20260923`。
- 基点及当前 HEAD：`ca05b90e3767c0945ed7a5b5b73f7cc1423da665`。无科学源码修改、无提交、无 push。
- Python 3.9.25、NumPy 1.23.5。审计使用单线程库设置，CPU affinity 为 0–3。

用户本轮指令及附件第 7 节决定当前任务。旧 `TASK.md` 中的 4 CPU 小时、仅写 `/tmp`、重训与其他 stage 等历史执行安排不适用于本轮。本轮上限维持 2 CPU 小时、4 线程、16 GiB，缓存定位不超过 30 分钟；未启动旧任务或下一轮实验。

## 已恢复与缺失的输入

| 对象 | 本次核验 |
|---|---|
| 官方 SIFT1M base | `dataset/sift1m/hf_download/sift_base.fvecs`，516,000,000 bytes，SHA-256 与历史官方成员完全一致 |
| GIST1M base | `dataset/gist/gist_base.fvecs`，3,844,000,000 bytes；本次仅核对大小，未重新证明完整内容哈希 |
| 两套样本索引 | 从原代码及固定种子再生成，均与 9/3 报告 SHA-256 完全匹配；每套 16,384 个唯一索引，前后 8,192 行交集为零 |
| 两套 residual 面板 | 均缺失；每套预期 16,384×128，fvecs 为 8,454,144 bytes |
| 原 PCA／coarse／assignments 状态 | 均未在所查位置找到，无法从 raw base 重放原 residual |
| 原面板来源记录及变换哈希 | 未找到 `STAGE_SOURCE.txt` 或可核验原状态的缓存记录；不能给不存在的输入填写哈希 |

SIFT base 哈希：`21f66e2975057b5728ba56de1c825bac4f4d89d596609ae985741c6242631816`。

已恢复索引哈希：

- SIFT：`a5ef3954b0d240e9b5fcf59690a559d458b6f05b7c55ca3c0e6bdb648c61a104`。
- GIST：`5cb6868406e6f184abe689058992ab9e8aba52a312c64aa34345a51e7826966d`。

历史 `/tmp/correlated-pair-allocation`、`/tmp/saq-correlated-pair-allocation` 和 `/tmp/saq-structured-2d-modeling` 现存文件数均为零。持久 SAQ、dataset、resources、worktrees 和 Hugging Face cache 的文件名检查没有找到原面板或变换；`.codex/worktrees` 不存在。具体范围和原始输出见 `cache_audit.log`。这不证明其他主机或离线备份也没有副本。

仅有 base 和索引不足以确定原 PCA 坐标、全维粗聚类路由和 residual。重新训练会违反本轮约束，且不能视为恢复原输入，因此未执行。未进行下载、解包、query/GT 内容读取、ANN 基准或其他实验。

## 代码审查与校验状态

已读取适用 `AGENTS.md`、研究规范、`diagnostic.py`、索引生成和 stage 提取代码，以及 9/2、9/3 报告。
`pair_curve` 的局部 PCA 与码本只由 fit 学习；轴曲线已在函数内计算，但没有从 `PairCurve` 对外暴露。若输入可用，所需扩展应限于暴露这些曲线、增加 V/S 分配及相应输出。当前数据门槛失败，未编写无法完成真实输入校验的实验扩展。

| 必做检查 | 本次状态 |
|---|---|
| 原索引、唯一性、折间不重叠 | 通过；不等同于完成整个新实验的 fit-only 校验 |
| 每臂精确 512 bits | 未运行；无可用 residual 输入 |
| 新实现的 fit/eval 无泄漏 | 未运行；未实现／拟合四臂 |
| E 与受限标量 DP 等价及统一 tie-breaking | 未运行数值检查；源码审查与附件的可行域推导一致 |
| 自由 S 的 fit SSE ≤ E | 未测量；仅有固定曲线下的可行域包含关系 |
| `git diff --check`、来源哈希及输出完整性 | 在交付前核验，详见 `verification.log` |

这些发现是输入和源码证据，**不是新的科学实验结果**。没有构建、没有完整实验复现；性能状态为 `PERFORMANCE_NOT_YET_MEASURED`。

## 配对效应与位分配效应

| 效应 | 冻结的比较 | 本次结论 |
|---|---|---|
| 配对／局部变换效应 | CORR-S 对 ADJ-S、EA-S 的绝对 held-out SSE | 未测量，不能判断相关性配对是否有效 |
| 组约束／分配的独立增量 | CORR-E 对 CORR-S | 未测量，不能判断是否存在正则化收益 |
| 经验曲线相对方差代理的效应 | CORR-E 对 CORR-V | 未测量 |

候选仍固定为 CORR-E，未从历史表挑选新候选。旧报告中 E 相对各自 U 的增益不能替代上述比较。GIST 目标范围仍是全维路由后的前 128 维；这是复用历史诊断样本，不能声称独立测试、GIST 全维效果、Recall/QPS 收益或新颖性。

因此本次选择 `BLOCKED`，不选择 `STOP_CURRENT_FORMULATION`、`PARK_INCONCLUSIVE` 或 `ELIGIBLE_FOR_CONFIRMATION`。没有证据支持通过或否决 5% 门槛。

## 资源及持久证据

缓存定位窗口：20:31:23–20:39:57 HKT（514 秒）。两份持久审计命令合计实测 CPU 为 1.31 秒，最大 RSS 为 44,648 KiB（约 43.6 MiB）；分别有 120 秒 CPU／墙钟和 16 GiB 地址空间硬限制。数字仅覆盖 `audit.sh` 与 `cache_audit.py`，不将未统一计时的前期目录浏览、worktree 创建和独立审查冒充为完整测量。量化实验 CPU 为 0，输出行数为 0；没有实验运行时内存或总模型字节测量。

本目录持久保存：原附件、`config.tsv`、`availability.tsv`、两份原始审计日志、命令脚本、资源记录、源文件哈希、恢复索引及其验证表、独立缓存审查、交付校验日志和 `SHA256SUMS`。未生成空白或估计 SSE 来冒充 48 行结果；payload／码本／变换／查表字节尚无实测值。

## 最小后续动作

仅建议从已有备份恢复两数据集原 `residual_nlist1024.fvecs`（每个约 8.1 MiB）及其样本顺序、来源与变换哈希凭据；或恢复原 PCA、nlist1024 coarse、assignments 与对应 transformed base 以重放同一面板。索引无需再寻找，已持久恢复。

在可核验缓存出现前保持暂停。没有启动下一轮，没有发送导师邮件。当前无剩余实验进程；缓存审计 agent 已完成。
