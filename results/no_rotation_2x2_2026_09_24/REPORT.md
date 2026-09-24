# 去掉段内随机旋转：2×2 实际编码实验结果

实验日期：2026-09-24。执行状态：**COMPLETE_ENCODER_DIAGNOSTIC**。
研究判断：**停止当前“去掉段内 QR＋本轮 nearest-lattice 曲线位分配”形式，不追加实验。**

已按附件 README 完成真实 SIFT1M／GIST1M 实验。保留全局 PCA 和 nlist=1024 残差表示时，取消段内 QR 没有带来实测位分配收益；相反，实际编码重建误差在 SIFT 两折增加约 68%，在 GIST 两折增加约 19%。这不支持把该组合继续推进为 SAQ 改进。

## 主要结果

主指标是实际生成六轮调整后量化码，再按 `q *= ||x||² / <x,q>` 重缩放得到的 held-out 每向量 SSE，越小越好。不是方差规划代理，也不是只在 fit 上计算的 nearest-lattice SSE。

| 数据／折 | IDENTITY / UNIFORM | IDENTITY / ADAPTIVE | QR / UNIFORM | QR / ADAPTIVE | 去掉 QR 后误差增加 |
|---|---:|---:|---:|---:|---:|
| SIFT-128 A→B | 896.463668 | 896.463668 | 533.171802 | 533.171802 | 68.1379% |
| SIFT-128 B→A | 902.256470 | 902.256470 | 537.430456 | 537.430456 | 67.8834% |
| GIST-960 A→B | 0.00855326411 | 0.00855326411 | 0.00720069218 | 0.00720069218 | 18.7839% |
| GIST-960 B→A | 0.00856235443 | 0.00856235443 | 0.00721451941 | 0.00721451941 | 18.6823% |

完整 16 行结果及附加误差指标见 [summary.tsv](measurement/summary.tsv)，4 行预定对照见 [contrasts.tsv](measurement/contrasts.tsv)。上表“增加”以 QR 为分母；原始 contrasts 中相应 gain 是其负值。

- 无旋转时，自适应相对原位宽的收益：四个组合均 **0%**。
- 固定 QR 下，自适应相对原位宽的收益：四个组合均 **0%**。
- IDENTITY/ADAPTIVE 相对 QR/UNIFORM 的收益：依次为 **−68.1379%、−67.8834%、−18.7839%、−18.6823%**。
- 因为两种 rotation 内的 U/A 都完全相同，单独去旋转的对照、双方都允许 adaptive 的对照也得到上述同一组负值；“去旋转额外释放的绝对分配收益”均为 0。

## 如何解释

**分配效应：**不是收益太小而被舍入到零。所有 8 个“数据／折／rotation”组合的自适应分配都没有任何坐标对改变位宽；保存的 fit 曲线在选中位宽和原位宽上的总目标相同。24 组 U/A 逐向量误差数组（含三种误差指标）逐元素完全一致。当前分配器因此没有提供新的编码方案，评价端也没有出现正负收益抵消。

**旋转效应：**在相同分段、逐段位预算、编码调整和因子预算下，identity 的实际重建误差更高。该结果说明，本轮固定 QR 在此编码原型和面板上具有正面作用；不能用“取消随机混合会暴露更多方差差异”直接推出实际编码改善。本轮也没有复现历史规划代理约 30% 的“真实收益”，两者目标函数不同。

**停止范围：**nearest-lattice 曲线的 DP 最优只针对可加的 fit 代理目标；六轮调整和重缩放后的实际误差是耦合目标。因此结果只能否定当前所测组合的继续投入价值，不能证明所有无旋转位分配、所有 data-aware 方法或任何其他优化器都不可能有效。

README 的两个跨数据集／两折 5% 投入信号均未满足：无旋转分配增益为零，且新组合不如 QR baseline。没有启动额外种子、参数、分段、优化器或检索实验。

## 实验与预算匹配

两数据集均沿用历史冻结的 16,384 个索引，两折各 8,192 行。上游全维 PCA／coarse 是上一轮已训练模型，本轮只重放。分段由各折 PCA fit 样本的方差通过既有 planner 选择；四臂共享分段。位宽分配仅使用 residual fit，评价行不用于选择分段或位数。identity 不做局部 PCA、中心化或重新配对，相邻坐标对内两轴等位宽。

| 数据 | 两折得到的分段：坐标区间／每轴 bits | payload | 因子预算 | 每向量合计 | adaptive 额外共享位宽表 |
|---|---|---:|---:|---:|---:|
| SIFT-128 | `[0,128):4` | 512 bits | 64 bits | 72 B | 64 B／共享模型 |
| GIST-960 | `[0,64):11; [64,256):6; [256,576):4; [576,832):2; [832,960):0` | 3648 bits | 256 bits | 488 B | 416 B／共享模型 |

GIST 使用完整 960 维残差；最后 128 维的零位宽尾段按省略能量计入所有臂，并非从误差中删除。因子按每个正位宽段 64 bits 计账。这是本实验的匹配预算；float64 原型没有实物打包并验证生产因子精度，因此不能称为已测得完整部署内存。共享旋转／上游模型等开销也不应混入上述每向量预算。

QR 使用固定 `20260903` 种子，并按段边界派生矩阵；矩阵哈希保存在 [rotations.tsv](measurement/rotations.tsv)。它代表这一个固定 QR 设定，不是遍历所有生产旋转。

## 执行与校验

- 主机：`rwcpu8.cse.ust.hk`；Python 3.9.25、NumPy 1.23.5、GCC 11.5.0。固定 Faiss 缓存沿用上一轮版本，没有安装、下载或重训。
- 新独立 worktree：`/rwproject/kdd-db/kluaq/worktrees/saq-no-rotation-20260924`，分支 `no-rotation-2x2-20260924`，基准提交 `35f38aa7ae668a4734d7a08a9bcf73aa00da9a75`。
- 原 data-aware worktree 仅作输入／缓存来源，保持干净。原始仓库未提交内容未改动。
- 附件 7 个文件的 SHA-256 全部匹配；原脚本未改。`opportunity_reference.py` 与 Git 对应文件仅相差末尾一个额外 LF，代码语义相同，保留附件原始字节并记录差异。
- 编译成功，附件六项测试全部通过。官方两份 base、冻结索引以及旧模型／面板均通过哈希检查。
- SIFT-128 和 GIST-960 的全维导出成功；其前 128 维与已保存 head 的最大绝对差均为 **0**，原 coarse assignment 也通过逐行比对。
- 正式运行验证 QR 正交性和能量守恒、精确 payload、重建 SSE 与 `||x||² tan²(theta)` 的数值恒等式。另行只读复核确认 16 行 summary、4 行 contrasts、3,840 行分配和 21,120 行 fit 曲线一致；4 个 NPZ 的 48 个逐向量数组均有 8,192 行，其均值与表格完全一致。详见 [review.md](review.md)。
- 本轮未做生产 C++ 编码器位级一致性、Recall／QPS 或理论误差保证验证。复用了历史诊断样本，两折不构成独立数据集，也不是未使用的最终测试集。

实际执行原附件入口，第二个参数指定新 worktree 的持久输出目录：

```bash
env -u NO_ROTATION_BOUNDED_RUN PYTHONDONTWRITEBYTECODE=1 \
  bash /rwproject/kdd-db/kluaq/worktrees/saq-no-rotation-20260924/research/no_rotation_experiment_20260924/run_remote.sh \
  /rwproject/kdd-db/kluaq/worktrees/saq-data-aware-minimal-20260923 \
  /rwproject/kdd-db/kluaq/worktrees/saq-no-rotation-20260924/results/no_rotation_2x2_2026_09_24
```

## 资源及持久交付

整个正式脚本使用 CPU affinity `{0}`、BLAS/OpenMP 单线程、一小时 wall 硬上限、16 GiB 地址空间上限；最终 exit 0。GNU time 记录总 CPU **71.93 秒**、总 wall **34 分 46.35 秒**、最大单任务 RSS **527,339,520 B（约 503 MiB）**。编码测量本身约 59.61 CPU 秒、60.56 wall 秒。其余时间主要等待持久文件系统 I/O；资源记录没有把等待时间冒充计算成本。只读结果复核额外约 0.16 CPU 秒。

本目录保存运行日志、依赖哈希、全维面板与来源记录、16 行汇总、4 行对照、fit 曲线、位数分配、QR 哈希和逐向量 NPZ。整个正式脚本的资源记录为同级 [no_rotation_2x2_2026_09_24.resources.txt](../no_rotation_2x2_2026_09_24.resources.txt)，源码及原 README 位于新 worktree 的 `research/no_rotation_experiment_20260924/`。

建议归档本轮负结果，停止当前形式。本次没有自动 commit、push、发邮件或启动下一轮实验。未来若重新开启，应先提出能解释并检验“可加代理目标与最终耦合编码误差不一致”的具体问题，再单独授权实验；本轮不代为扩展。
