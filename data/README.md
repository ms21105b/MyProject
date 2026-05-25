# Data

本项目的主分析数据是：

```text
data/raw/EcommData_CSV.csv
```

## Main Dataset

- 文件格式：CSV，分号分隔
- 时间范围：`2022-01-01` 至 `2024-12-31`
- 数据规模：102,771 条订单，3,900 个客户
- 金额格式：逗号小数，例如 `46,9`
- 关键字段：`Purchase Date`、`Promo Code Used`、`Previous Purchases`、`Purchase Amount (USD)`、`Churn`
- 口径说明：`Previous Purchases` 表明客户在数据窗口前可能已有购买历史，因此 cohort 使用 first observed purchase month，而不声称是真实生命周期首购。
- `Location` 可用于构建 `segment × location × month` 的类 geo/region 面板，服务于 Synthetic Control 准 A/B 模拟；但原始数据仍不包含随机实验分组、真实发券触达记录或促销试点上线时间。

## Smoke-Test Sample

`data/raw/customer_behavior_purchase.csv` 是脚本生成的小样本，只用于验证代码结构和快速 smoke test，不用于作品集结论。

如需重新生成小样本：

```bash
python scripts/make_sample_data.py
```

## Why Raw Data Is Excluded From Public GitHub

Kaggle 数据集通常有独立许可和下载条款。公开作品集仓库建议只提交代码、SQL、说明和可复现输出，不直接提交原始 Kaggle 数据。

## Expected Commands

运行真实数据分析：

```bash
python scripts/run_analysis.py --input data/raw/EcommData_CSV.csv
```

运行 Synthetic Control 准 A/B 扩展：

```bash
python scripts/run_scm_analysis.py --input data/raw/EcommData_CSV.csv --treatment-start 2024-01-01 --outcome active_customer_rate
```

构建 SQLite 数据库：

```bash
python scripts/build_sqlite.py --input data/raw/EcommData_CSV.csv
```

运行测试：

```bash
python -m unittest discover -s tests
```
