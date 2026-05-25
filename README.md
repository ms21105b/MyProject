# E-commerce Promo Code & Retention Analysis

面向数据分析实习投递的作品集项目：基于 2022-2024 年真实电商购买行为数据，分析促销码使用、first observed cohort 留存、RFM 客户分层、促销敏感度和未来 180 天不活跃风险，并扩展 Synthetic Control 准 A/B 反事实模拟，用于设计分层促销策略。

> 重要边界：本项目分析的是促销码使用与用户行为之间的相关性，不声称促销码导致留存、复购或流失变化。若要做因果结论，需要 A/B 测试、随机发券、准实验设计或额外实验数据。

## Business Question

促销码使用行为与用户复购、留存和未来不活跃风险之间有什么关系？平台应如何针对不同客户价值层级和促销敏感度设计促销策略？

## Dataset

- 数据文件：`data/raw/EcommData_CSV.csv`
- 时间范围：`2022-01-01` 至 `2024-12-31`
- 数据规模：102,771 条订单，3,900 个客户
- 总销售额：USD 5,331,988.70
- 促销码订单占比：13.19%
- 订单级 `Churn` 标签占比：7.35%；客户级 `Churn` 标签占比：8.56%
- 格式：CSV，分号分隔，金额字段使用逗号小数格式，例如 `46,9`

`Previous Purchases` 显示客户在数据窗口前已有购买历史，因此本项目的 cohort 是 **first observed purchase cohort**，代表客户在当前数据集内首次出现的月份，不代表生命周期真实首购月份。

## Methodology

1. **Data validation and cleaning**
   - 解析分号分隔 CSV 和逗号小数金额。
   - 统一 `Promo Code Used`、`Subscription Status`、`Churn` 为 0/1 字段。
   - 验证核心字段缺失率、日期范围、金额合法性、订单数和客户数。

2. **Monthly KPI analysis**
   - 构建月度订单数、活跃客户数、销售额、AOV、促销码使用率和客户级 `Churn` 标签率。
   - 2024-12 是销售额最高月份，销售额约 USD 284,590.40，订单数 4,406。

3. **Promo-code behavior analysis**
   - 对比促销码订单与非促销码订单的订单量、客户覆盖、销售额、AOV、历史购买次数和 `Churn` 标签。
   - 促销码订单 AOV 为 USD 51.56，非促销码订单 AOV 为 USD 51.93，差异很小。
   - 促销码订单覆盖 3,476 个客户，但订单占比只有 13.19%，说明促销码触达广但使用频率不高。

4. **First observed cohort retention**
   - 按客户在数据集内首次出现月份定义 cohort。
   - 后续月份只要客户再次购买，即视为该 cohort 在对应月份留存。
   - 输出 first observed cohort retention matrix 和 heatmap，用于观察观测窗口内客户留存变化。

5. **RFM + promo sensitivity segmentation**
   - RFM 只负责价值/活跃分层：High Value、Potential Loyalist、At Risk High Spender、Dormant / Churn Risk、Regular。
   - 促销敏感度单独分层：No Promo、Moderate Promo、High Promo。
   - 输出 RFM segment、promo sensitivity、以及 segment x promo sensitivity 组合矩阵。

6. **180-day future inactivity risk model**
   - 不使用全周期特征预测全周期 `Churn`，避免时间泄漏。
   - 训练快照：用 `2023-06-30` 及以前行为预测未来 180 天是否无购买。
   - 测试快照：用 `2023-12-31` 及以前行为预测未来 180 天是否无购买。
   - 模型用于识别未来不活跃风险信号，不作为生产级预测系统。

7. **Synthetic Control quasi A/B extension**
   - 基于 cutoff-safe 的 `segment × location × month` 面板，为促销试点构造 synthetic counterfactual。
   - 默认 pseudo-treated unit 为 `Dormant / Churn Risk | Montana`，`treatment_start = 2024-01-01`，outcome 为 `active_customer_rate`。
   - 输出 donor weights、actual vs synthetic path、gap path、placebo MSPE ratio 和 injected lift recovery。
   - 该模块用于准 A/B 设计与反事实模拟，不改变当前项目“相关性分析”的主结论。

## Key Findings

- **促销码不是高 AOV 的明显驱动信号。** 促销码订单 AOV 为 USD 51.56，非促销码订单 AOV 为 USD 51.93；在该数据中，促销码订单没有表现出更高客单价。
- **促销码覆盖广但使用频率低。** 3,476/3,900 个客户至少使用过一次促销码，但促销码订单只占全部订单的 13.19%。
- **No Promo 客户未来不活跃风险最高。** No Promo 客户 424 人，未来 180 天不活跃率为 35.01%，明显高于 Moderate Promo 的 2.13% 和 High Promo 的 1.96%。
- **Dormant / Churn Risk 是主要召回对象。** 该群体 952 人，平均购买 9.89 次，未来 180 天不活跃率为 21.81%。
- **High Value 客户近期活跃且风险最低。** High Value 客户 851 人，平均购买 42.21 次，平均消费 USD 2,229.70，未来 180 天不活跃率为 0。
- **未来不活跃模型表现适合解释风险，而非自动决策。** 时间切分随机森林在测试快照 ROC-AUC 为 0.912；正类 recall 为 0.808，但 precision 为 0.238，说明模型更适合做召回名单的初筛，而不是直接自动投放。
- **SCM 准 A/B 模块已实现但只作模拟解释。** 默认模拟中，`Dormant / Churn Risk | Montana` 的 active customer rate 处理前拟合为 `GOOD_PRE_FIT`，但 placebo rank 为 10/50、经验 p-value 为 0.20，不支持强因果表述；injected lift simulation 能恢复 3%、5%、10% 人工 uplift 的方向。

## Strategy Recommendations

- **High Value + High/Moderate Promo**：保留会员权益、提前购、免邮、专属客服等非价格型权益，避免过度折扣稀释利润。
- **Potential Loyalist**：用新品推荐、搭配推荐和轻量满减提高购买频次，避免过早训练用户只在打折时购买。
- **At Risk High Spender + High Promo**：优先召回但控制折扣强度，组合使用个性化推荐、会员权益和限时关怀券。
- **Dormant / Churn Risk**：使用低成本触达、限时召回券和历史偏好品类推荐，提高再次购买概率。
- **No Promo 客户**：优先用低门槛首券或免邮权益测试促销接受度，避免直接大额补贴。

## Quick Start

安装依赖：

```bash
pip install -r requirements.txt
```

运行完整分析：

```bash
python scripts/run_analysis.py --input data/raw/EcommData_CSV.csv
```

也可以省略 `--input`，默认读取真实数据文件：

```bash
python scripts/run_analysis.py
```

运行 Synthetic Control 准 A/B 扩展：

```bash
python scripts/run_scm_analysis.py --input data/raw/EcommData_CSV.csv --treatment-start 2024-01-01 --outcome active_customer_rate
```

也可以在主流程中显式加入 SCM 扩展：

```bash
python scripts/run_analysis.py --include-scm
```

生成 SQLite 数据库并练习 SQL：

```bash
python scripts/build_sqlite.py --input data/raw/EcommData_CSV.csv
sqlite3 data/processed/ecommerce.sqlite < sql/03_business_kpis.sql
```

运行测试：

```bash
python -m unittest discover -s tests
```

## Outputs

- `outputs/validation_report.csv`
- `outputs/monthly_kpis.csv`
- `outputs/promo_comparison.csv`
- `outputs/cohort_retention.csv`
- `outputs/rfm_segments.csv`
- `outputs/segment_summary.csv`
- `outputs/promo_sensitivity_summary.csv`
- `outputs/segment_promo_matrix.csv`
- `outputs/churn_time_split_feature_importance.csv`
- `outputs/churn_time_split_metrics.json`
- `outputs/scm_panel.csv`
- `outputs/scm_feasibility_summary.csv`
- `outputs/scm_weights.csv`
- `outputs/scm_gap_path.csv`
- `outputs/scm_placebo_summary.csv`
- `outputs/scm_injected_lift_summary.csv`
- `outputs/scm_summary.csv`
- `outputs/scm_run_metadata.json`
- `figures/monthly_sales_promo_usage.png`
- `figures/cohort_retention_heatmap.png`
- `figures/promo_vs_no_promo.png`
- `figures/promo_sensitivity_summary.png`
- `figures/segment_strategy_matrix.png`
- `figures/scm_actual_vs_synthetic.png`
- `figures/scm_gap_path.png`
- `figures/scm_placebo_mspe_ratio.png`
- `figures/scm_injected_lift_recovery.png`
- `reports/project_report.md`
