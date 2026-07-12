# CO-0 v2 通俗进度说明

日期：2026-07-12

## 一句话版本

我们目前还没有在发明一个新的 CAQ 算法。我们正在先验证一个更基础的
研究前提：

> SAQ 生产实现只做六轮 CAQ adjustment。它距离同一码本中的真正最优
> 编码还有多远？这种差距是否被 SAQ 的短维度、高 bit segment 特别放大？

整套 `V1/V2`、`A0/A1/A2`、`B0/B1` 是一组逐级 gate：先证明测量尺子
正确，再冻结实验规则，最后才读取真实数据并判断这个 limitation 是否
存在。

当前最简状态是：

```text
尺子已经造好并验证通过
实验成本已经确认可承受
真实实验规则已经预注册
B1 真实 base-only limitation screen 正在由另一会话执行
尚无最终科学结论
尚无新方法或论文贡献
```

## 1. 我们究竟在比较什么

SAQ 会把 residual vector 切成多个 segment，并为不同 segment 分配不同
bit 数。例如冻结的 GIST 计划是：

```text
64@11 | 192@6 | 320@4 | 256@2 | 128@0
```

`64@11` 表示这个 segment 有 64 个维度，每个维度使用 11 bit。这里的
bit width 与阶段编号 `V2-B1` 中的字母 `B` 没有关系。

对每个 residual segment，实验比较四种编码：

| Arm | 通俗解释 | 在实验中的作用 |
|---|---|---|
| `lvq_init` | CAQ adjustment 开始前的初始答案 | 确定总共有多少可改善空间 |
| `caq_r6` | 当前 SAQ 生产实现，只运行六轮 | 真正被检查的对象 |
| `caq_local_fixed_point` | 使用完全相同的规则，一直运行到没有坐标可再改变 | 判断问题是否只是“六轮太少” |
| `corrected_exact` | 完整枚举关键事件，得到这个离散码本中的全局最优答案 | 作为实验标准答案，不作为部署方法 |

`corrected_exact` 会比较慢，但它在这里相当于考试答案，而不是准备部署
到查询路径中的新 encoder。

实验真正关心的是：

```text
当前 r=6 还留下多少“初始编码到精确最优”之间的改善机会？
```

如果 `r=6` 已经接近 exact，这个方向关闭。如果普通 CAQ 多运行一些轮次
就能达到 exact，这也只是参数问题。只有当 local fixed point 仍明显落后，
而且差距集中在 SAQ 自己制造的短维度、高 bit segment，并影响当前
estimator，才可能构成 SAQ-specific limitation。

## 2. 编号是什么意思

这些不是 SAQ 或 E-RaBitQ 论文里的标准术语，而是本项目用于控制研究
过程的内部 checkpoint。

- `CO-0`：可以理解为 CAQ optimality 的零号 limitation gate；尚未进入
  method development。
- `V1`、`V2`：实验协议版本。
- `A` 阶段：造尺子、验证尺子，只使用数学推导和 synthetic inputs。
- `B` 阶段：使用冻结的真实 base/index data 进行 limitation measurement。
- `0/1/2`：同一阶段中按顺序执行的 checkpoint。

完整流程是：

```text
V1：尝试把官方 Extended-RaBitQ artifact 当作精确尺子
    └── 官方尺子不满足 exact/width parity，V1 停止

V2：建立明确区分于官方 artifact 的独立精确尺子
    V2-A0  写清定义和 exactness proof
       ↓
    V2-A1  实现并用小规模穷举与边界输入验证
       ↓
    V2-A2  用 synthetic inputs 检查实验成本
       ↓
    V2-B0  在看真实结果之前冻结样本、指标和 PASS/NO-GO 规则
       ↓
    V2-B1  在真实 GIST/CIFAR base residual 上执行 limitation screen
       ↓
    NO-GO 或 CONDITIONAL PASS
```

最容易混淆的一点是：

> A 阶段 PASS 只表示测量尺子可用；B0 PASS 只表示考试规则已经冻结。
> 只有 B1 才会回答 SAQ 是否真的存在这个 limitation。

## 3. V1 做了什么，为什么停止

V1 原计划直接使用官方 Extended-RaBitQ artifact 作为 exact oracle。

官方-source parity 检查发现：

- `fast_quantize` 没有评价初始化的 `t_start` code；
- 它在一个合法的 `D=64, B=3` 输入上错过全局最优；
- 官方 IVF 只支持总位宽 `{3,4,5,7,8,9}`；
- SAQ 冻结计划还需要 `B=2,6,11`；
- `B=11` 的 magnitude 需要 10 bit，但官方接口通过 `uint8_t` 返回，
  会发生 narrowing。

因此 V1 的结论不是“SAQ 没有问题”，而是：

> 官方 executable artifact 不能充当这次实验所需的精确标准答案。

V1 在 CO-0A 停止，原始 CO-0B 没有继续执行。这个失败结论仍然保留，
V2 没有追溯性地把官方 artifact 改称 exact。

## 4. V2-A0：在数学上定义并证明新尺子

V2 定义了独立的 `complete-event oracle`。A0 解决的是“为什么这个算法
确实包含全局最优 code”，包括：

- 把 binary32 输入精确分解为整数与公共的二次幂；
- 使用整数 cross product 确定 event 的精确顺序；
- 不让浮点 epsilon 决定最优 code；
- 明确评价 initial state；
- 明确 zero、tie、padding 和 subnormal 语义；
- 用 `uint32_t` 支持 `B=11`，避免 byte narrowing；
- 证明完整 event 集合包含一个全局方向-code optimum；
- 记录运算、整数位宽、临时内存和永久字节开销。

V2-A0 已 PASS。主要依据是
`docs/saq_caq_co0_v2_oracle_specification_2026_07_11.md` 中的 Lemma 1--3。

仍有一项 source-review debt：最初没有取得完整 E-RaBitQ 正文和 appendix，
因此目前的 exactness 是自包含证明，不是对论文逐项 cross-check。这不等于
当前 oracle 已被证伪，但在形成 paper-level attribution 或 novelty claim 前
应当补齐。

## 5. V2-A1：验证证明与 C++ 实现一致

数学推导正确并不保证实现没有错误。A1 使用能够完全穷举的小问题和专门
设计的边界输入，对 independent oracle 进行验证。

已经通过的检查包括：

- 128 个 complete-codebook brute-force cases；
- V1 的 109 个历史 deterministic fixtures；
- 官方 encoder 失败的 D64 initial-state counterexample；
- zero、tie 和 padding；
- subnormal 和最大 finite binary32；
- `B=11` widened magnitude；
- 130 个 centered-grid、cosine、rescale 和 estimator mapping cases；
- invalid-input rejection；
- Release 与 ASAN/debug runs。

全部 PASS。因此 `corrected_exact` 目前可以作为可信的实验标准答案，而不
是另一个未经验证的近似 encoder。

## 6. V2-A2：确认 exact labeling 成本可承受

Complete-event oracle 的主要工作量近似随下式增长：

```text
D × (2^(B-1) - 1)
```

所以 GIST 的 `64@11` 是最昂贵的 cell。

A2 只使用 deterministic synthetic binary32 vectors，测量冻结计划中的九种
正 bit `(D,B)` cells，没有读取真实 GIST/CIFAR objective gap。

冻结成本估计为：

```text
GIST 50,000 vectors：约 6.146 CPU-hours
CIFAR 50,000 vectors：约 1.823 CPU-hours
合计：约 7.969 CPU-hours
硬停止上限：24 CPU-hours
```

因此 V2-A2 PASS，样本量没有因为 `B=11` 昂贵而事后缩小。

7.969 小时只是 exact labeling 的 CPU estimate，不是严格 wall-clock ETA；
它没有覆盖全部 I/O、其他 encoder arms 和最终统计处理。

## 7. V2-B0：在看答案之前冻结考试规则

B0 是 final preregistration。它防止在看到结果以后：

- 只报告效果最好的 segment；
- 更换 rotation seed；
- 改变 10% materiality threshold；
- 删除不支持结论的数据集；
- 因为 exact 太慢而删除 `B=11`；
- 增加新的 bit width、control 或 subgroup 来挽救方向。

B0 已冻结：

- GIST 和 CIFAR 各 50,000 个 base vectors；
- 512 个 IVF cells 下的 cluster-stratified samples；
- disjoint base-residual pairs；
- 三个 logical rotation seeds；
- 所有 native segments 和 bit widths；
- 四个 encoder arms；
- same-dimension uniform-`B=4` controls；
- whole-positive-view uniform-`B=4` control；
- 24 个预先声明的 hypotheses；
- cluster bootstrap 和 Holm multiple-testing correction；
- 24 CPU-hour exact-label ceiling；
- 固定的 PASS、NO-GO 和 stop rules。

B0 只读取一维 assignment labels 来冻结 sample/pair inventory，没有运行
encoder，也没有读取 objective 或 estimator gap。B0 PASS 不表示 SAQ
存在 limitation，只表示实验规则已经不能根据结果修改。

## 8. V2-B1：真正回答研究问题

B1 才第一次在真实 GIST/CIFAR base residual 上比较四个 encoder arms。

### 8.1 差距是否足够大

对任意 arm `a`，核心比例可通俗理解为：

```text
剩余机会比例 =
    (arm 的 error factor - exact error factor)
    /
    (初始编码 error factor - exact error factor)
```

- `0` 表示 arm 已经达到 exact；
- `1` 表示 arm 和初始编码一样，没有恢复任何机会；
- `0.10` 表示仍留下初始到 exact 总改善空间的 10%。

两个数据集的 leading high-bit segment 都必须满足：

```text
r6 剩余比例的 95% lower confidence bound >= 0.10
local-fixed-point 剩余比例的 95% lower confidence bound >= 0.10
```

要求 local fixed point 也留下 material gap，是为了排除“普通多跑几轮就
解决”的解释。

### 8.2 差距是否由 SAQ segmentation 放大

每个数据集的 leading segment 必须明显差于：

1. 相同 vectors、相同 dimension，但统一使用 `B=4` 的 control；
2. 所有 lower-bit native segments；
3. 整个 positive residual view 使用 uniform `B=4` 的 control。

如果 uniform controls 也有同样的 gap，这只是一般 CAQ encoding 现象，
不是 SAQ-specific limitation。

### 8.3 差距是否影响当前 estimator

当前 search path 不消费存储的 `fac_error` 字段。因此 theoretical error
factor 变小不能单独通过 gate。

B1 还会把 code/factors 送入当前不变的 full-code estimator，检查把 leading
segment 从 `caq_r6` 换成 `corrected_exact` 后，是否在两个数据集都降低
normalized absolute inner-product error。Unscaled error 也必须方向一致。

三个 rotation seeds 都必须支持相同方向。一个 seed 很好、其余 seeds
反向，也会返回 NO-GO。

## 9. 第一次 B1 为什么在编码前停止

第一次 registered B1 command 完成了真实 artifact 的 hash/shape preflight，
随后发现 rotation hash mismatch，并在第一次 encoder call 前停止：

```text
encoding_rows = 0
pair_rows = 0
exact_cpu_ns = 0
code_bytes = 0
```

原因是：

- B0 使用非 AVX/FMA 的 Release profile 生成 27 个冻结 rotation matrices；
- 原 B1 runner 在 SIMD translation unit 中重新生成 rotation；
- Eigen Householder QR 在不同 floating-point/SIMD profile 下得到数值非常
  接近、但 byte 不完全相同的 matrices。

因为 preregistration 要求 byte identity，runner 正确地在测量前停止。

修复把 rotation generation 隔离到固定 B0 编译参数的 translation unit 中，
同时保留 CAQ encoder、packer 和 estimator 的 SIMD flags。修复已通过：

```text
27/27 runner-linked rotation hashes
Release validation PASS
ASAN validation PASS
```

这是 instrument correction，不是协议修改或科学结果。

## 10. 当前进度快照

截至本文写作时：

```text
canonical branch：saq-caq-corrected-oracle-v2
last committed revision：2da5e9f
V2-A0：PASS
V2-A1：PASS
V2-A2：PASS
V2-B0：PASS
V2-B1 instrument validation：PASS
V2-B1 first preflight：STOPPED before encoding
V2-B1 rotation correction：PASS
corrected registered B1 execution：正在另一个 Codex 会话中运行
final scientific decision：尚不可用
method contribution：尚未建立
```

运行时输出目录是：

```text
/tmp/saq-caq-co0-v2-b1-registered-2da5e9f
```

这个 runtime state 已经领先于 commit `2da5e9f` 中的 `TASK.md`；该文件仍
记录“rerun not authorized”，因为它是在 corrected run 启动前提交的。
运行结束以后，需要单独验证 output manifest、shards、资源上限和 frozen
hypotheses，然后才能生成并提交科学判定。

不要因为看到 runner 正在运行就假定 limitation 已经成立；在结果文件
完成并通过 preregistered summarizer 之前，没有可报告的 objective 或
estimator conclusion。

## 11. B1 最终结果可能怎样解释

### 情况一：`r6` 几乎等于 exact

返回 NO-GO。有限轮 CAQ 不是值得继续的 SAQ limitation。

### 情况二：`r6` 有差距，但 local fixed point 消除了差距

返回 NO-GO。这说明问题只是 adjustment rounds 或 stopping condition，
不能作为新的机制贡献。

### 情况三：`r6` 和 fixed point 都有差距，但 uniform controls 也一样

返回 NO-GO。这是 generic CAQ encoding behavior，而不是 SAQ segmentation
特有的放大效应。

### 情况四：两个数据集的 leading high-bit segment 都出现稳定、显著且
estimator-visible 的额外差距

返回 CONDITIONAL PASS。这只证明一个 SAQ-specific limitation 存在，随后
才允许开展低成本 certificate 或 deterministic repair 的 primary-source/
theory review。

即使是 CONDITIONAL PASS，也还不是论文贡献。后续方法还必须优于简单
增加 CAQ rounds 或全面使用 exact E-RaBitQ，并保持原有 index bytes、
global plan 和 query-time work。

## 12. 阅读顺序

如果只想逐步理解，建议按下面顺序阅读：

1. 本文：整体逻辑和当前状态；
2. `docs/saq_caq_co0a_official_source_parity_2026_07_11.md`：V1 为什么停止；
3. `docs/saq_caq_co0_v2_reopening_corrected_oracle_protocol_2026_07_11.md`：
   为什么以及如何开启 V2；
4. `docs/saq_caq_co0_v2_oracle_specification_2026_07_11.md`：exactness proof；
5. `docs/saq_caq_co0_v2_a1_synthetic_validation_2026_07_11.md`：实现验证；
6. `docs/saq_caq_co0_v2_a2_synthetic_cost_evidence_2026_07_11.md`：成本 gate；
7. `docs/saq_caq_co0_v2_b0_final_preregistration_2026_07_11.md`：最终实验规则；
8. `docs/saq_caq_co0_v2_b1_rotation_build_correction_2026_07_12.md`：第一次
   B1 停止及 instrument correction。

在 B1 完成后，还应新增最终 execution evidence 和 go/no-go memo；在那之前，
本文只是一份进度说明，不是实验结果报告。
