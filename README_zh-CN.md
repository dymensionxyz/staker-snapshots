# Dymension 质押者快照

此代码库包含 Dymension 质押者的历史快照。这些快照由 Dymension 验证者提供。快照遵循以下 CSV 格式：

文件名：`validator_YYYYMMDD.csv`

格式：质押的 DYM 及其质押者

```csv
质押者地址, 质押的 dym数量;
质押者地址, 质押的 dym数量;
...
质押者地址, 质押的 dym数量;
```

* 请注意，这不是抗女巫攻击的：一个人可以创建多个钱包，表现为多个钱包的持有者。
