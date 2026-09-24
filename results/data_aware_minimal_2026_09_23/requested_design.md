# Data-aware 坐标对量化：有边界的证据复核与最小实验设计

日期：2026-09-23。范围：导师提出的 data-aware 坐标对／位数分配方向。状态：已完成文档、源码和相关原始文献复核；本次没有运行新实验。

## 1. 决策

**保留一轮有上限的强基线补证，暂不作为新主线，也不把整个方向判死。**

已有证据足以停止“固定 SAQ 段内随机旋转之后，再做当前形式的坐标对位分配”。它不足以否定不强制该旋转的 data-aware 方案。另一方面，旧实验已经包含学习得到的局部 PCA、标量量化器和位分配；不能把后续包装成“第一次尝试 data-aware”。

真正待回答的是：**在相同编码预算下，相关性配对带来的局部变换，是否比普通 data-aware 标量位分配和已有配对基线多带来可泛化的收益？**

本轮不增加 query-aware 目标、dynamic/adaptive search、AMIPS、端到端索引优化或新的神经量化器。Data-aware 在这里指利用数据库分布学习表示／量化／位数；并不自动等同于使用查询分布。

## 2. 证据范围与可复核程度

仓库：`Ufowoqqqo/SAQ`；分支：`saq-correlated-pair-allocation`；本次检查的提交：`ca05b90e3767c0945ed7a5b5b73f7cc1423da665`。下方仓库链接均固定到此提交。

本次直接核对了研究报告及 `diagnostic.py`、`opportunity.py` 的目标函数、量化与分配逻辑。数值来自已提交报告，尚未独立重跑；报告所述 `/tmp` 原始输出未随报告提交，其存在性和字节一致性本次没有验证。以下分别标注“历史报告结果”“源码推导”“尚缺证据”。

| 证据 | 支持的结论 | 不能推出的结论 |
|---|---|---|
| 9/2 原始坐标诊断 [R1]：局部 PCA＋两路 Lloyd 标量量化；CORR 的跨组分配收益约 SIFT 3.1–4.1%、GIST 1.5%；GIST 的相关性配对在均匀组预算下优于邻接配对约 16.6–17.9% | 配对效应和跨组分配效应必须分开；已有 data-aware 实验 | 全维 GIST、官方 SIFT1M 或真实检索收益；该 SIFT 输入是 SIFT10M 的切片 |
| 9/3 表示阶段诊断 [R2]：官方 SIFT1M/GIST1M，诊断均取前 128 维；PCA、残差阶段的分配收益显著 | 表示方式改变可分配的误差空间 | 哪种配对的绝对误差最低；各行百分比的分母不同 |
| SAQ 机会分解 [R3]：固定一个段内 Gaussian-QR 旋转，经验曲线分配后没有坐标对改变位宽；编码角度损失收益为零 | 当前固定旋转、分段、预算、候选位宽下的这套方案没有通过门槛 | 所有旋转、联合变换与分配、所有 data-aware 量化都无效 |
| 8/3 最近配对基线 [R4]：经验 SSE 最优匹配相对 EA 的 Recall 改善远小于当时 +0.002 门槛 | 不能再次以“优于邻接配对”作为主要证据 | 所有 data-aware 编码器均已测过；EA 是自实现的二维 OPQ-P 特化，不是完整 OPQ |

阶段诊断中，跨坐标对分配相对各自均匀组预算的平均 SSE 改善如下。这张表用于定位问题，**不能按列直接给配对方法排名**。

| 数据／表示，均为 128 维诊断 | CORR | EA | ADJ |
|---|---:|---:|---:|
| SIFT raw | 4.867% | 1.984% | 2.875% |
| SIFT PCA head | 26.618% | 1.747% | 40.590% |
| SIFT residual，nlist=1024 | 20.496% | 0.057% | 22.545% |
| GIST raw | 1.514% | 0.138% | 5.802% |
| GIST PCA head | 20.982% | 8.788% | 30.815% |
| GIST residual，nlist=1024 | 9.417% | 0.533% | 13.934% |

另有两个解释边界：PCA 后 CORR 配对跨折重合仅 1/64，残差阶段约 8–14/64，提示配对身份不稳定；方差与边际收益的高相关性只是描述性证据，不能代替强基线对比或因果归因。[R2]

### 必须修正的数值口径

1. SAQ 机会分解中，旋转前 SIFT 约 28–31%、GIST 约 6.3–6.4% 的改善来自 `variance / 2^bits` **规划代理目标**，不是实测无旋转编码误差，更不是 Recall。[R3, C2]
2. 经验分配部分在 fit 上用未调整 lattice 的 SSE 构造可加曲线，评价时用六轮调整后的 `norm² × tan²(angle)`。二者不是同一个目标。其 DP 最优不能称为真实编码损失的全局 oracle 上界。[C2]
3. 旋转是固定种子生成并记录哈希的一个 Gaussian-QR 矩阵；可以说符合所检查的段内旋转设定，不能说已逐位重放所有生产旋转。正交旋转本身可逆，“旋转破坏信息”也不是准确表述。[C2]
4. 标量诊断的 512-bit payload，不能与 SAQ 的 72 B SIFT／488 B GIST 总预算直接比较。后者还包含因子字节，GIST 使用全维和非均匀分段。[R3]

## 3. 最接近的已有工作与源码判断

本次只核对足以限定新颖性的最接近工作，不做无限文献搜索：

| 工作 | 已覆盖的思想 | 对当前方案的要求 |
|---|---|---|
| Brandt, CVPR 2010, Transform Coding [P1] | 变换编码、按数据分配各分量位数、非均匀标量量化 | “学习变换＋非均匀分配”本身不能作为新颖性 |
| Park et al., BMVC 2014, OTC [P2] | 根据各分量估计分布优化位分配 | 经验失真曲线优于纯方差规则，也不自动构成新方法 |
| Quantization Beyond Uniform Bit Allocation，2026 预印本 [P3] | 固定存储预算下 data-dependent 分桶及非均匀 PQ/SQ 位分配 | 若以后转向分桶或 Matryoshka 表示，必须做直接定位；本轮不增加其复现 |

仓库综述还列出 OPQ、BAPQ、DSPQ 和 SAQ 自身的分段／位宽选择。[R5] 本轮不是穷尽检索，也未独立复现这些论文；不据此宣称“无任何新颖性”。

### 一个可以直接证明的边界

`diagnostic.py::pair_curve` 在固定配对和局部 PCA 后，为组 g 构造：

\[
C_g(B)=\min_{b_1+b_2=B}\{D_{g1}(b_1)+D_{g2}(b_2)\},\qquad B\in\{6,\ldots,10\}.
\]

`allocate_bits` 再求总组预算为 512 的最小和。这等价于对固定变换后的 128 个标量坐标直接求解：

\[
\min\sum_iD_i(b_i),\quad \sum_i b_i=512,\quad 1\le b_i\le9,\quad 6\le b_{g1}+b_{g2}\le10.
\]

因此，**此处“pair allocation”的分配层，是带组约束的经典标量位分配**。去掉组约束后的标量 DP 可行域更大，fit 上的最优 SSE 不可能更高。held-out 上不保证这一关系，因为组约束可能起正则化作用；并列最优还需统一 tie-breaking。[C1，源码推导]

这不排除“如何配对、如何学局部变换”有价值，也不涉及真正的二维联合 VQ。它意味着下一步应检验配对／变换的增量，而不是重复证明不均匀预算优于均匀预算。

## 4. 最小实验：只补强基线，不开新路线

### 唯一主问题

在不强制 SAQ 段内随机混合的 data-aware 标量量化设定中，**CORR 配对＋局部 PCA 的收益能否超越简单配对＋普通位分配？**

### 固定输入与计算边界

- 仅用已有官方 SIFT1M、GIST1M 的 `residual_nlist1024` 诊断面板，各取前 128 维、16,384 行，按现有 A→B／B→A 两折，各 8,192 行 fit 和评价。沿用已记录的样本索引与变换来源。
- 这是历史诊断面板补证，不是新的独立测试集。所有本轮学习决策只使用 fit；不按评价结果调配对、位宽或阈值。GIST-128 结论只属于该子空间。
- 三种既有配对：ADJ、CORR_GREEDY、EA。每种配对都学习自身局部 PCA；同一配对内所有实验臂共享变换和已拟合标量码本。
- 所有方案的向量 payload 都是精确 512 bits。位数元数据、局部变换、码本字节以及查表项数另外列出；不把 payload 相同说成总系统内存相同。
- 本轮不重复 raw、PCA-only、nlist=4096，不重训完整 IVF，不扫旋转种子，不建百万级索引，不测 QPS。
- 执行预算：最多一次工作时段、2 小时累计 CPU、最多 4 线程、峰值内存 16 GiB。输入定位／恢复最多 30 分钟；缺缓存、需大规模下载或超过上限即停止并交阻塞说明。以上是运行上限，不是承诺本周完成。

### 四个实验臂

| 臂 | 固定的规则 | 要回答的问题 |
|---|---|---|
| U：均匀组预算 | 每组 8 bits；组内两轴分配仍按 fit 经验误差选择 | 重现旧报告的分母；它不是每坐标恒定 4 bits |
| V：方差分配 | 用 `variance_i × 2^(-2b_i)` 选择位数；与 E 相同的位数范围、组约束和全局预算；评价使用同一套 Lloyd 码本 | 经验曲线是否比经典方差代理带来泛化改善 |
| E：现有经验组分配 | 当前 `pair_curve`＋`allocate_bits`，组预算 6–10，轴预算 1–9 | 待审核方法 |
| S：自由标量分配 | 同样的经验标量曲线，直接按轴 DP；轴预算 1–9、总预算 512，取消组的 6–10 限制 | E 是否只是标准标量分配的受限版本；是否存在可重复的正则化收益 |

V 的 `2^(-2b)` 是本轮标量高码率代理对照；不要悄悄替换成 SAQ 的 `2^(-b)`，两者定义不同。V 不声称完整复现 Brandt 或 OTC。

共 2 数据集 × 2 折 × 3 配对 × 4 臂 = **48 行结果**；码本曲线复用，不是 48 次索引构建。另做一次很小的等价性检查：直接标量 DP 加回组约束时，应与 E 的 fit 最优目标一致；用统一 tie-breaking 验证可重放的位数选择。

### 指标与比较规则

主指标为同一评价面板上每向量绝对 SSE；同时记录 fit SSE、评价总 SSE、相对增益、位数直方图、超出旧组范围的 S 组数、时间和内存。

预先指定候选为 **CORR-E**，分别与 **CORR-S、CORR-V、ADJ-S、EA-S** 比较：

\[
G(C;B)=1-\mathrm{SSE}_{eval}(C)/\mathrm{SSE}_{eval}(B).
\]

不要只汇报各配对对 U 的百分比；不同配对必须比较绝对 SSE。不要从 48 行中挑一个赢家作为新候选。两折共享来源，不能当两个独立数据集计算显著性。

必做正确性校验只有：预算精确、无 fit/eval 泄漏、受限 DP 等价、自由 S 的 fit SSE 不高于 E（容许浮点误差）。这些直接检验核心论证，不增加无关测试。

### 停止与继续条件

| 结果 | 决定 |
|---|---|
| 预算／数据来源／fit-only 条件不成立，或缓存无法恢复 | `BLOCKED`：列出缺失项，不填估计数字，不扩大基础设施工作 |
| CORR-E 只赢 U，不能稳定赢预先指定的 data-aware 基线 | `STOP_CURRENT_FORMULATION`：当前形式没有独立增量；不否定所有 data-aware 方法 |
| 仅一折或一个数据集改善，或改善小于 5% | `PARK_INCONCLUSIVE`：记录局部现象，暂不追加种子、参数或数据集 |
| 两数据集、两折中，对四个指定基线都至少改善 5% | `ELIGIBLE_FOR_CONFIRMATION`：先核查泄漏和 DP；可能是组约束正则化或配对效应，不直接宣称新颖性 |

5% 是为控制投入预设的实用门槛，不是统计显著性阈值或普适标准。即使最后一行成立，也只允许提出下一轮方案：保留未使用样本、确认 GIST 全维效果、定位机制并核算总空间。只有这些成立，才值得设计查询排序／Recall 对照；本轮不自动执行。

另行记录配对效应：若 CORR-E 与 CORR-S 相当，而 CORR-S 稳定优于 ADJ-S、EA-S，应写成“存在配对／局部变换信号，但没有坐标对分配的独立增量”。暂停当前分配方案时保留这个观察，不把它误写成配对无效；它也不自动触发新实验。

## 5. 一个仍未回答、但本轮不混入的问题

“取消 SAQ 段内随机旋转后，真实编码损失是否下降？”目前只有规划代理正信号，缺少对应的实际编码闭环。

如果后续研究目标明确转为 SAQ 编码器改进，最小桥接对照应是：identity／固定 QR × 原位宽／经验分配，在相同全维分段、payload、因子字节下，实际编码并评价相同角度损失。这是单独的 2×2 机制检查；identity 是去掉该段内随机旋转，不代表移除已有全局学习变换。它既不能替代本轮强基线，也不能凭自己证明检索贡献，因此当前不并行启动。

## 6. 向导师汇报时可用的事实边界

可以汇报：已重新区分“固定随机旋转的负结果”和更一般的 data-aware 设定；发现早期方案已有 data-aware 成分；当前缺口是相对于常规 data-aware 位分配的增量证据，已设计限额补证。

暂不能汇报：data-aware 已被证伪／已经有新方法；去掉旋转后真实编码改善 30%；已有 Recall/QPS 收益；本周一定完成。

下一次沟通的交付物应是“一张强基线表，或一份具体阻塞说明，及继续／暂停决定”。无 meeting 的周发简短 progress；有 meeting 则带同一份结果。审稿任务优先级与研究交付时间另行安排，不在这里替用户承诺日期。

## 7. 可直接交给执行 Codex 的任务说明

```text
Audit and minimally extend the existing correlated-pair diagnostic in
Ufowoqqqo/SAQ, using commit ca05b90e3767c0945ed7a5b5b73f7cc1423da665
as the evidence reference. Read applicable AGENTS.md and preserve unrelated
work. Work in an isolated branch/worktree if needed. Do not push or publish.

Goal: test whether CORR_GREEDY pairing plus local PCA and empirical pair-bit
allocation adds held-out SSE value beyond ordinary data-aware scalar allocation.
Do not start an ANN benchmark or a new research branch.

Inspect research/correlated_pair_allocation/diagnostic.py and the Sept 2/3
reports. Recover existing official SIFT1M and GIST1M residual_nlist1024
panels and sample/provenance hashes. Use first 128 dimensions, 16,384 rows,
existing two-way 8,192-row cross-fit. Stop with BLOCKED if provenance or cached
inputs cannot be recovered within 30 minutes. No large downloads or IVF retraining.

For ADJ, CORR_GREEDY and the existing EA specialization, reuse fit-only local
PCA and scalar Lloyd codebooks. Expose per-axis fit/eval distortion curves
already computed by pair_curve. Evaluate four arms at exactly 512 payload bits:
U: 8 bits/group, empirical fit-optimal internal split;
V: variance_i * 2^(-2*b_i) allocation, b_i in 1..9, group sums in 6..10;
E: existing empirical pair-curve DP;
S: empirical per-axis DP with b_i in 1..9 and no group-sum constraint.
Use the same codebooks to evaluate all arms within each pairing/fold.

Check exact budgets, fit/eval separation, equivalence of E to a scalar DP
with identical group constraints, and fit_SSE(S) <= fit_SSE(E) within tolerance.
Use a common deterministic tie rule. Keep existing output semantics intact.
Compare absolute held-out SSE across pairings, not their separate gains vs U.

Write 48 summary rows plus allocation/provenance records to durable repo output
paths, not only /tmp. Record code/input hashes, seeds, commands, raw SSE,
payload and shared metadata/codebook/transform bytes, timing and memory.
Predeclared candidate: CORR-E. Comparators: CORR-S, CORR-V, ADJ-S, EA-S.
No tuning using evaluation rows and no candidate selection after viewing results.

Cap the entire run at 2 CPU-hours, 4 threads and 16 GiB peak memory, within one
work session. Stop rather than expand scope. Do not rerun raw/PCA-only/nlist4096,
rotation sweeps, full OPQ, matching optimization, query-aware losses, Recall/QPS,
or the separate SAQ identity-vs-QR bridge.

Return one of BLOCKED / STOP_CURRENT_FORMULATION / PARK_INCONCLUSIVE /
ELIGIBLE_FOR_CONFIRMATION. Eligibility requires >=5% held-out SSE reduction
against every specified comparator in both folds of both datasets; it is a
practical continuation gate, not proof of novelty or statistical significance.
Clearly label GIST-128 and reused historical diagnostic samples. Provide a
short report and a proposed next step only; do not auto-launch confirmation.
```

## 来源

- [R1：9/2 原始坐标诊断](https://github.com/Ufowoqqqo/SAQ/blob/ca05b90e3767c0945ed7a5b5b73f7cc1423da665/docs/research/correlated_pair_allocation_base_diagnostic_2026_09_02.md)
- [R2：9/3 表示阶段归因](https://github.com/Ufowoqqqo/SAQ/blob/ca05b90e3767c0945ed7a5b5b73f7cc1423da665/docs/research/correlated_pair_allocation_stage_attribution_2026_09_03.md)
- [R3：9/3 SAQ 机会分解](https://github.com/Ufowoqqqo/SAQ/blob/ca05b90e3767c0945ed7a5b5b73f7cc1423da665/docs/research/correlated_pair_allocation_saq_opportunity_decomposition_2026_09_03.md)
- [R4：8/3 最近配对基线](https://github.com/Ufowoqqqo/SAQ/blob/ca05b90e3767c0945ed7a5b5b73f7cc1423da665/docs/research/nonadjacent_pairing_closest_baseline_result_2026_08_03.md)
- [R5：最近原始文献综述](https://github.com/Ufowoqqqo/SAQ/blob/ca05b90e3767c0945ed7a5b5b73f7cc1423da665/docs/research/correlated_pair_allocation_closest_primary_work_review_2026_09_03.md)
- [C1：diagnostic.py](https://github.com/Ufowoqqqo/SAQ/blob/ca05b90e3767c0945ed7a5b5b73f7cc1423da665/research/correlated_pair_allocation/diagnostic.py)
- [C2：opportunity.py](https://github.com/Ufowoqqqo/SAQ/blob/ca05b90e3767c0945ed7a5b5b73f7cc1423da665/research/correlated_pair_allocation/opportunity.py)
- [P1：Brandt, Transform Coding for Fast Approximate Nearest Neighbor Search in High Dimensions, CVPR 2010](https://iacl.ece.jhu.edu/proceedings/cvpr2010/papers/0557.pdf)
- [P2：Park et al., Optimized Transform Coding for Approximate KNN Search, BMVC 2014](https://www.bmva-archive.org.uk/bmvc/2014/papers/paper001/index.html)
- [P3：Quantization Beyond Uniform Bit Allocation, arXiv:2608.19388](https://arxiv.org/abs/2608.19388)
