# 去掉 SAQ 段内随机旋转：可执行 2×2 编码实验

2026-09-24。**当前状态：实现和本地合成数据校验已完成；真实数据实验未执行。**

当前 Work 会话对 `kluaq@rwcpu8.cse.ust.hk` 的只读 SSH 探测失败：
`Could not resolve hostname ... Temporary failure in name resolution`。
未尝试绕过网络限制，未修改远程仓库，未 commit/push。

## 这次具体回答什么

固定上游全维 PCA 和 IVF nlist=1024 残差表示，取消量化前的**段内随机旋转**，看按坐标对分配位数是否降低真实编码误差。

本实验不是原始坐标“完全不做任何旋转”：全局 PCA 明确保留。段内 identity 臂完全不做旋转、局部 PCA、重新中心化或配对重排。采用相邻坐标对，同一对的两个坐标使用相同位宽。

四臂：IDENTITY/UNIFORM、IDENTITY/ADAPTIVE、QR/UNIFORM、QR/ADAPTIVE。
同一个数据集／折的四臂共享同一个分段和逐段总位数预算。分段由该折的 PCA fit 样本通过既有 SAQ planner 确定；不看评价折。

SIFT 为 128 维，GIST 为完整 960 维；仍使用已冻结的 16,384 个样本，A→B、B→A 各 8,192 行。仅一个 nlist 和一个固定 QR 种子，不扩展数据或参数。

## 与上一轮不同

- 不调用 `diagnostic.py::pair_curve`；没有局部 PCA 和 Lloyd 标量码本。
- 实際使用原 opportunity 代码中的共享 segment max lattice 编码和六轮 CAQ 风格调整。
- 自适应分配复用 nearest-lattice SSE 曲线＋精确 DP，只看 fit 数据。
- 评价真正生成调整后的量化码，使用 CAQ 的 rescaling：`q *= ||x||² / <x,q>`；直接计算重建 SSE，并检查它与 `||x||² tan²(theta)` 恒等。
- 每向量 payload 与每个正位宽段的 64-bit 因子预算在四臂完全一致；新增共享位宽表独立报告，不把同 payload 说成总空间完全一样。
- 零位宽尾段按被省略向量能量计入所有臂。

**限制：**分配器优化的是可加 nearest-lattice SSE，评价是耦合的调整后误差，故负结果只能评价这套分配器。该 float64 混合位宽原型未与生产 C++ 编码器建立逐位一致性；不支持生产性能、误差概率界、Recall/QPS 或新颖性结论。尤其去掉随机旋转后，不能直接沿用依赖随机旋转的理论误差保证。

## 文件

- `no_rotation.py`：16 行主结果、4 行对照结果、逐向量误差、训练曲线、位数分配与随机矩阵哈希。
- `opportunity_reference.py`：固定提交 `35f38aa7ae668a4734d7a08a9bcf73aa00da9a75` 的原 opportunity 实现快照；原文件头部的旧描述只属于历史脚本，本次真实编码评价由新 runner 完成。
- `test_no_rotation.py`：无旋转输入直通、无评价折泄漏、精确预算、实际重建误差、零尾段、错误维数六项校验。
- `export_panels.cpp`：只重放已有全维 PCA/coarse 模型，不重训；从官方 base 的冻结索引读取样本，恢复全维面板，并与已保存的 128 维 head 检查一致性。
- `run_remote.sh`：校验输入和模型哈希、编译 exporter、运行测试、导出面板、运行测量。单核和一小时总 wall 上限，16 GiB 地址空间上限；不下载数据。

## 在已连接服务器的会话运行

解压本目录至服务器持久目录，然后执行：

```bash
bash /absolute/path/no_rotation_experiment_20260924/run_remote.sh \
  /rwproject/kdd-db/kluaq/worktrees/saq-data-aware-minimal-20260923
```

默认输出为该工作树下 `results/no_rotation_2x2_2026_09_24/`。输出存在即拒绝覆盖。原有结果不会被更改。若使用其他输出目录，请作为第二个参数传入**绝对路径**。

缓存的 Faiss 库／头文件／BLAS 不在预期位置时，可显式设置：
`SAQ_FAISS_LIBRARY`、`SAQ_FAISS_SOURCE`、`SAQ_BLAS_LIBRARY`。必须使用上一轮的固定 Faiss，不自动安装或替换版本。

本地环境没有 Faiss 库，因此 C++ exporter 尚未完成编译和真实模型加载校验；远程脚本会先编译并检验旧 head，一旦不一致就停止。远程运行成功前，不应将本交付标为实验完成。

## 结果怎么读

1. `allocation_gain_identity_pct`：无旋转时，自适应相对原位分配的真实收益；这是导师建议的直接检验。
2. `allocation_gain_qr_pct`：相同分配方法在固定 QR 下的收益。
3. `identity_adaptive_vs_qr_uniform_pct`：新组合是否胜过原旋转均匀方案。即使第 1 项为正，这项也可能为负。
4. `identity_uniform_vs_qr_uniform_pct`：单独去旋转的影响。
5. `identity_adaptive_vs_qr_adaptive_pct`：双方都允许相同自适应分配时的对照。

原始绝对误差为主，不只汇报百分比。跨两数据集两折都达到 5% 只作为后续投入信号，不是显著性检验；本轮无论正负都不自动启动下一轮。

若 identity 下有收益，但仍输给 QR baseline，应汇报“无旋转下分配有效，但尚无 SAQ 改善”。若没有收益，应汇报“当前 nearest-lattice 曲线分配未在该设定建立收益”，不能否定所有 data-aware 量化。

## 本地完成的验证

六项新数值校验通过；Python 编译检查和 shell 语法检查见 `LOCAL_CHECKS.txt`。
没有真实 SIFT/GIST 数字，没有将合成数据测试冒充实验结果。
