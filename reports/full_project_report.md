# E-commerce Promo Code 与客户留存分析 —— 完整项目报告

---

## 一、项目概述

### 1.1 研究背景

在电商运营中，促销码（promo code）是平台最常用的营销工具之一。然而，促销码的使用行为与客户复购、留存、流失之间到底是什么关系？平台应该如何针对不同价值的客户设计差异化的促销策略？这些问题直接关系到营销预算的分配效率和客户生命周期价值的最大化。

### 1.2 研究目的

本项目旨在通过分析 2022 至 2024 年的真实电商订单数据，回答以下核心问题：

- **促销码使用行为**与客户复购率、留存率、未来不活跃风险之间存在怎样的关联？
- 如何基于客户的历史行为对其进行**价值分层**和**促销敏感度分类**？
- 平台应如何针对不同层级客户制定**差异化的促销策略**？

### 1.3 分析边界声明

本项目所有结论均为**相关性分析**，不声称促销码**导致**留存提升或流失下降。要得出因果结论，需要 A/B 测试、随机发券实验或准实验设计，而当前数据集不包含实验分组或随机化字段。

---

## 二、数据介绍

### 2.1 数据来源

数据来自 Kaggle 电商行为数据集，文件为 `EcommData_CSV.csv`，存储于 `data/raw/` 目录。

### 2.2 数据规模与时间范围

| 指标 | 数值 |
|------|------|
| 订单总数 | 102,771 条 |
| 客户总数 | 3,900 人 |
| 时间范围 | 2022-01-01 至 2024-12-31 |
| 总销售额 | USD 5,331,988.70 |
| 促销码订单占比 | 13.19% |
| 订单级 Churn 标签占比 | 7.35% |
| 客户级 Churn 标签占比 | 8.56% |

### 2.3 原始字段说明

数据集包含 20 个原始字段，核心字段如下：

| 字段名 | 说明 | 类型 |
|--------|------|------|
| Customer ID | 客户唯一标识 | 整数 |
| Purchase Date | 订单日期（格式 DD.MM.YYYY） | 日期 |
| Purchase Amount (USD) | 订单金额（逗号小数格式） | 数值 |
| Promo Code Used | 是否使用促销码（Yes/No） | 布尔 |
| Previous Purchases | 客户在数据窗口前的历史购买次数 | 整数 |
| Churn | 流失标签（Yes/No） | 布尔 |
| Subscription Status | 订阅状态（Yes/No） | 布尔 |
| Category / Season / Location | 品类、季节、地区 | 类别 |
| Payment Method / Shipping Type | 支付方式、配送方式 | 类别 |
| Age / Gender | 年龄、性别 | 数值/类别 |
| Review Rating | 评分 | 数值 |
| Discount Applied | 是否使用折扣 | 布尔 |
| Frequency of Purchases | 购买频率标签 | 类别 |

### 2.4 数据质量说明

- **分隔符**：CSV 使用分号（`;`）分隔，非逗号。
- **金额格式**：使用逗号作为小数分隔符（如 `46,9` 表示 46.9 美元），需要转换为点号小数。
- **布尔字段**：`Promo Code Used`、`Churn`、`Subscription Status` 等字段存储为 `Yes`/`No` 字符串，需映射为 0/1。
- **Previous Purchases 字段**：该字段表明大量客户在数据窗口开始前已有购买历史，因此数据集内的首次购买**不等于**客户生命周期的真实首购。这是项目中 "first observed cohort" 命名约定的原因。

---

## 三、项目结构

```
ecommerce-promo-retention-analysis/
├── data/
│   ├── raw/                          # 原始数据
│   │   ├── EcommData_CSV.csv         #   Kaggle 真实数据集（102,771 条）
│   │   └── customer_behavior_purchase.csv  # 脚本生成的样例数据（用于测试）
│   ├── processed/                    # 处理后数据
│   │   └── ecommerce.sqlite          #   SQLite 数据库（由 build_sqlite.py 生成）
│   └── README.md
├── src/promo_retention/              # 核心 Python 包
│   ├── __init__.py
│   ├── config.py                     # 项目路径配置、原始字段名映射
│   ├── data.py                       # 数据加载、清洗、特征工程
│   ├── metrics.py                    # 业务指标计算、RFM 分层、队列留存
│   ├── modeling.py                   # 180 天未来不活跃风险预测模型
│   ├── synthetic_control.py          # SCM 准 A/B 反事实模拟
│   ├── validation.py                 # 数据验证与清洗前后对比
│   └── plotting.py                   # Matplotlib/Seaborn 绑图
├── scripts/                          # 可执行脚本
│   ├── run_analysis.py               # 主流程：一键运行完整分析
│   ├── run_scm_analysis.py           # SCM 准实验扩展分析
│   ├── build_sqlite.py               # 将清洗后数据写入 SQLite
│   └── make_sample_data.py           # 生成 schema 兼容的样例数据集
├── sql/                              # SQL 查询（与 Python 分析平行）
│   ├── 01_schema.sql                 # 建表语句
│   ├── 02_data_quality.sql           # 数据质量检查
│   ├── 03_business_kpis.sql          # 月度 KPI、促销对比、品类分析
│   ├── 04_cohort_retention.sql       # 队列留存、首购促销分层留存
│   ├── 05_rfm_segmentation.sql       # 客户 RFM 与促销敏感度分层
│   └── 06_scm_panel.sql              # SCM 面板 SQL 口径示例
├── notebooks/
│   └── 01_eda_retention_rfm.ipynb    # Jupyter 探索性分析笔记本
├── tests/
│   ├── test_methodology_improvements.py  # 方法论正确性单元测试
│   └── test_real_data_pipeline.py       # 真实数据集成测试
├── outputs/                          # 分析结果 CSV / JSON
├── figures/                          # 可视化绑图 PNG
├── reports/
│   ├── project_report.md             # 简短版报告（英文）
│   └── full_project_report.md        # 本文件：完整中文项目报告
├── requirements.txt                  # Python 依赖
├── README.md                         # 项目说明
└── resume.md                         # 简历素材与面试问答
```

---

## 四、研究方法设计

本项目采用**定量二次数据分析**方法，整体流程包含六大步骤：

### 4.1 研究流程总览

```
原始 CSV 加载
    │
    ▼
数据清洗与验证
    ├── 分号分隔解析、逗号小数转换
    ├── Yes/No → 0/1 映射
    ├── 缺失值处理、异常金额过滤
    └── 清洗前后对比报告
    │
    ▼
月度 KPI 构建
    ├── 月度销售额、订单量、活跃客户数
    ├── 月度 AOV、促销码使用率
    └── 客户级 Churn 标签率
    │
    ▼
促销码行为分析
    ├── 促销 vs 非促销：订单量、AOV、客户数
    └── 促销 vs 非促销：Churn 率、历史购买次数
    │
    ▼
客户分层（三个维度）
    ├── 队列留存：首观测月份 cohort retention
    ├── RFM 价值分层：High Value / Potential Loyalist / At Risk / Dormant
    └── 促销敏感度分层：No Promo / Moderate Promo / High Promo
    │
    ▼
未来不活跃风险建模
    ├── 时间切分：训练快照 2023-06-30 / 测试快照 2023-12-31
    ├── 特征工程：RFM + 行为特征 + 类别特征
    └── Random Forest 分类器 + 特征重要性
    │
    ▼
SCM 准 A/B 扩展
    ├── cutoff-safe 的 segment × location × month 面板
    ├── Synthetic Control 反事实路径、placebo test
    └── injected lift simulation 验证方法灵敏度
    │
    ▼
策略建议输出
    └── 分层 × 促销敏感度交叉矩阵 + 针对性策略
```

### 4.2 数据清洗（Step 1）

**实现位置**：[src/promo_retention/data.py](src/promo_retention/data.py)

- `load_raw_csv()`：读取分号分隔 CSV，通过 `RAW_COLUMNS` 映射将原始列名（如 `Purchase Amount (USD)`）规范化为 snake_case（如 `purchase_amount`）。
- `clean_transactions()`：
  - 日期解析：`%d.%m.%Y` 格式转 `datetime`
  - 布尔字段映射：`Yes/No`、`True/False`、`1/0` 统一转为 0/1
  - 金额字段：逗号小数（`46,9`）转换为浮点数
  - 派生字段：`purchase_month`、`cohort_index`、`first_observed_purchase_month` 等
  - 质量过滤：剔除缺失 `customer_id`/`purchase_date`/`purchase_amount` 的行及 `purchase_amount <= 0` 的行

### 4.3 月度 KPI 分析（Step 2）

**实现位置**：[src/promo_retention/metrics.py](src/promo_retention/metrics.py) → `monthly_kpis()`

对每个自然月计算：
- 订单量、活跃客户数、总销售额（GMV）
- 平均订单价值（AOV）
- 促销码使用率（促销订单占比）
- 客户级 Churn 标签率（客户在该月任意订单被标记 Churn 即计为 churn，再按月取均值）

对应的 SQL 版本见 [sql/03_business_kpis.sql](sql/03_business_kpis.sql)，还额外包含品类维度的销售额与促销码使用率分析。

### 4.4 促销码行为对比（Step 3）

**实现位置**：[src/promo_retention/metrics.py](src/promo_retention/metrics.py) → `promo_comparison()`

按 `Promo` vs `No Promo` 分组，对比：
- 订单量、覆盖客户数、总销售额、AOV
- 平均历史购买次数（`Previous Purchases`）
- Churn 标签率

### 4.5 队列留存分析（Step 4a）

**实现位置**：[src/promo_retention/metrics.py](src/promo_retention/metrics.py) → `cohort_retention()` + `cohort_matrix()`

**核心概念**：由于数据集中客户在窗口前已有购买历史（`Previous Purchases` 字段非零），本项目使用 **first observed purchase cohort**（首观测购买队列）而非真实首购队列。

- **队列定义**：客户在数据集内首次出现的月份
- **留存定义**：在之后的某个月份，客户再次产生购买，即视为该队列在该月留存
- **队列指数（cohort_index）**：当前购买月份距离首次出现月份的月数差
- **留存率**：在给定 cohort_index 下仍活跃的客户数 / 队列初始总客户数

对应的 SQL 版本见 [sql/04_cohort_retention.sql](sql/04_cohort_retention.sql)，其中还包含按首购是否使用促销码分层（Promo First Observed Order vs No Promo First Observed Order）的队列留存分析。

### 4.6 RFM 客户价值分层（Step 4b）

**实现位置**：[src/promo_retention/metrics.py](src/promo_retention/metrics.py) → `rfm_segments()`

以数据集中最大日期 + 1 天为快照日期，对每个客户计算：

| 维度 | 计算方式 | 评分规则 |
|------|---------|---------|
| R（Recency） | 快照日期 - 最近一次购买日期（天数） | 越近分数越高（reverse=True），1-5 分位数评分 |
| F（Frequency） | 总购买次数 | 越多分数越高，1-5 分位数评分 |
| M（Monetary） | 总消费金额 | 越多分数越高，1-5 分位数评分 |

**评分机制**：使用 `pd.qcut` 按分位数将每个维度分为 5 档（1-5 分）。若 qcut 因数据重复值过多而失败，回退到全 3 分。

**分段规则**：

| 分段名称 | 条件 | 含义 |
|---------|------|------|
| High Value | R≥4 且 F≥4 且 M≥4 | 高价值高活跃客户 |
| Potential Loyalist | R≥3 且 F≥3（且不满足 High Value） | 有成长为高价值客户的潜力 |
| At Risk High Spender | R≤2 且 M≥4 | 曾经高消费但近期不活跃 |
| Dormant / Churn Risk | R≤2 且 F≤2 | 不活跃且有流失风险 |
| Regular | 以上均不满足 | 常规客户 |

**设计理念**：RFM 只负责价值/活跃分层；促销敏感度作为独立维度单独计算，避免混淆。

### 4.7 促销敏感度分层（Step 4c）

**实现位置**：[src/promo_retention/metrics.py](src/promo_retention/metrics.py) → `_promo_sensitivity()`

| 层级 | 定义 | 阈值 |
|------|------|------|
| No Promo | 从未使用过促销码 | promo_usage_rate = 0 |
| Moderate Promo | 使用过促销码，但使用率低于促销用户 75 分位数 | 0 < rate < P75 |
| High Promo | 使用过促销码，且使用率达到或超过促销用户 75 分位数 | rate ≥ P75 |

注意：阈值是在**使用过促销码的用户群体**内计算的，排除了 No Promo 客户，避免阈值被大量零值拉低。

### 4.8 未来 180 天不活跃风险模型（Step 5）

**实现位置**：[src/promo_retention/modeling.py](src/promo_retention/modeling.py)

**设计动机**：若使用 2022-2024 全周期行为特征预测同一全周期的 Churn 标签，会导致**时间泄漏**（未来信息泄漏到特征中）。因此本项目采用时间切分快照法：

**训练快照**：
- 截止日期：`2023-06-30`
- 特征：截止日期前的所有历史行为（recency、frequency、monetary、promo_usage_rate、类别偏好等）
- 标签：截止日期后 180 天内（至 `2023-12-27`）是否有任何购买。无购买 → `future_inactive_180d = 1`

**测试快照**：
- 截止日期：`2023-12-31`
- 特征：截止日期前的历史行为
- 标签：截止日期后 180 天内（至 `2024-06-28`）是否有购买

**特征工程**（[build_customer_features](src/promo_retention/modeling.py#L92)）：
- 数值特征：recency、frequency、monetary、AOV、promo_usage_rate、promo_orders、active_months、orders_per_active_month、previous_purchases、age、avg_review_rating
- 类别特征：gender、location、top_category、top_season、top_payment_method、top_shipping_type
- 派生特征：has_promo_order、distinct_categories

**模型架构**：
- 预处理：数值特征 → `SimpleImputer(median)` + `StandardScaler`；类别特征 → `SimpleImputer(most_frequent)` + `OneHotEncoder`
- 分类器：`RandomForestClassifier(n_estimators=200, min_samples_leaf=10, class_weight="balanced", random_state=42)`
- 整体为 `sklearn.pipeline.Pipeline`

### 4.9 数据验证

**实现位置**：[src/promo_retention/validation.py](src/promo_retention/validation.py)

两套验证机制：
- `validate_dataset()`：检查行数、客户数、必需列存在性、日期范围、金额合法性、布尔字段值域
- `summarize_cleaning()`：对比清洗前后的行数、客户数、销售额、促销码使用率

对应的 SQL 版本见 [sql/02_data_quality.sql](sql/02_data_quality.sql)。

### 4.10 Synthetic Control 准 A/B 扩展（Step 6）

**实现位置**：[src/promo_retention/synthetic_control.py](src/promo_retention/synthetic_control.py) + [scripts/run_scm_analysis.py](scripts/run_scm_analysis.py)

该模块把原本只写在方法论中的 Synthetic Control 设计落成可运行流程：

- 使用 `treatment_start` 之前的历史交易生成 RFM segment，避免用处理后信息定义客群。
- 构建 `segment × location × month` 面板，默认 outcome 为 `active_customer_rate`，并同步输出 `orders_per_customer`、`sales_per_customer`、`promo_usage_rate`。
- 用 `scipy.optimize` 求解非负且加总为 1 的 donor weights，生成 actual vs synthetic path、gap path、pre/post MSPE ratio。
- 对同一 donor pool 运行 placebo test，并通过 injected lift simulation 检查 3%、5%、10% 人为 uplift 是否能被 SCM 恢复。

这一步仍被定义为**准 A/B 模拟**：当前数据没有真实促销试点开始日或随机发券字段，因此 SCM 输出用于展示反事实评估能力，不作为促销效果的因果结论。

---

## 五、各模块作用总结

| 模块 | 文件 | 作用 |
|------|------|------|
| 配置 | `src/promo_retention/config.py` | 定义项目根目录、数据目录、输出目录路径；原始列名到规范列名的映射表 |
| 数据处理 | `src/promo_retention/data.py` | CSV 加载、列名规范化、类型转换、布尔映射、特征工程（cohort_index、首购月份等） |
| 指标计算 | `src/promo_retention/metrics.py` | 月度 KPI、促销对比、队列留存、RFM 分层、促销敏感度分层、分段汇总 |
| 预测建模 | `src/promo_retention/modeling.py` | 时间切分快照构建、客户级特征聚合、Random Forest 训练与评估、特征重要性输出 |
| SCM 准实验 | `src/promo_retention/synthetic_control.py` | 构建 cutoff-safe 客群-地区-月份面板、合成控制拟合、placebo test、injected lift simulation |
| 数据验证 | `src/promo_retention/validation.py` | 数据完整性检查、必需字段验证、布尔值域验证、清洗前后对比 |
| 可视化 | `src/promo_retention/plotting.py` | 月度趋势图、队列留存热力图、促销对比柱状图、分段策略矩阵散点图、促销敏感度摘要图、SCM 路径图 |
| 主脚本 | `scripts/run_analysis.py` | 一键执行全流程：加载→清洗→KPI→促销对比→留存→RFM→建模→输出 CSV/绑图；可选 `--include-scm` |
| SCM 脚本 | `scripts/run_scm_analysis.py` | 单独运行 Synthetic Control 准 A/B 扩展 |
| SQLite 构建 | `scripts/build_sqlite.py` | 将清洗后数据写入 SQLite，便于 SQL 练习 |
| SQL 查询 | `sql/01-06_*.sql` | 与 Python 分析平行的 SQL 实现，覆盖建表、数据质量、KPI、留存、RFM、SCM 面板口径 |
| 样例数据 | `scripts/make_sample_data.py` | 生成小规模 schema 兼容数据供测试使用 |
| 单元测试 | `tests/test_methodology_improvements.py` / `tests/test_synthetic_control.py` | 验证 first observed cohort、促销敏感度、时间切分快照、SCM 凸权重、placebo 与 uplift simulation |
| 集成测试 | `tests/test_real_data_pipeline.py` | 验证真实数据清洗后行数/客户数/日期范围/类型正确性、快照特征完整性 |

---

## 六、研究发现

### 6.1 促销码使用概况

- **覆盖广但频率低**：3,476/3,900（89.1%）的客户至少使用过一次促销码，但促销码订单仅占总订单的 13.19%。说明大部分客户只是偶尔使用促销码。
- **促销码与客单价无明显关联**：促销码订单 AOV 为 USD 51.56，非促销码订单 AOV 为 USD 51.93，差异极小（约 0.7%）。在该数据中，促销码不是高客单价的驱动信号。

### 6.2 客户分层分布

基于 RFM 分位数评分，3,900 名客户被分为五个层级：

| 分段 | 客户数 | 平均购买次数 | 平均消费金额 | Churn 率 | 未来 180 天不活跃率 |
|------|--------|------------|------------|---------|------------------|
| High Value | 851 | 42.21 | USD 2,229.70 | 0% | 0% |
| Potential Loyalist | 881 | 32.56 | USD 1,686.56 | 0% | 0.11% |
| Regular | 898 | 17.84 | USD 915.45 | 9.35% | 1.01% |
| At Risk High Spender | 318 | — | — | — | — |
| Dormant / Churn Risk | 952 | 9.89 | USD 503.76 | 16.60% | 21.81% |

### 6.3 促销敏感度与不活跃风险

| 促销敏感度 | 客户数 | 促销码使用率 | Churn 率 | 未来 180 天不活跃率 |
|-----------|--------|------------|---------|------------------|
| No Promo | 424 | 0% | 14.15% | **35.01%** |
| Moderate Promo | 2,352 | 12.26% | 7.91% | 2.13% |
| High Promo | 1,124 | 14.55% | 7.83% | 1.96% |

**关键发现**：从未使用促销码的客户（No Promo）未来不活跃风险（35.01%）远高于使用过促销码的客户。这提示 No Promo 客户可能是"价格敏感但未被触达"或"低参与度"群体，值得用低门槛促销手段测试激活。

### 6.4 未来不活跃风险模型表现

| 指标 | 训练快照 (2023-06-30) | 测试快照 (2023-12-31) |
|------|----------------------|----------------------|
| 客户数 | 3,819 | 3,867 |
| 正样本率（不活跃） | 10.03% | 5.25% |
| ROC-AUC | — | 0.912 |
| Accuracy | — | 0.854 |
| 正类 Recall | — | 0.808 |
| 正类 Precision | — | 0.238 |

**解读**：模型在不活跃客户识别上召回率达 80.8%，但精确率仅 23.8%——即模型预测为"不活跃"的客户中，约 76% 实际仍活跃。因此该模型适合作为**初筛名单工具**（帮助运营缩小关注范围），而不适合直接用于自动化决策（如自动发券）。

### 6.5 队列留存特征

- 首观测队列留存率随 cohort_index 增加呈下降趋势，符合预期。
- 后期队列（如 2024 年）的观测窗口较短，存在右删失，不适合直接与早期队列比较长期留存率。

---

## 七、策略建议

基于分层与促销敏感度的交叉分析，项目提出了以下分层促销策略：

| 客户群体 | 策略方向 | 具体建议 |
|---------|---------|---------|
| High Value + High/Moderate Promo | **保留与权益** | 会员专属权益、提前购、免邮、专属客服等非价格型权益，避免过度折扣稀释利润 |
| Potential Loyalist | **培育与引导** | 新品推荐、搭配推荐、轻量满减，提升购买频次，避免过早训练用户只在打折时购买 |
| At Risk High Spender + High Promo | **优先召回** | 控制折扣强度，组合使用个性化推荐、会员权益和限时关怀券 |
| Dormant / Churn Risk | **低成本触达** | 限时召回券、历史偏好品类推荐，提高再次购买概率 |
| No Promo | **测试激活** | 优先用低门槛首券或免邮权益测试促销接受度，避免直接大额补贴 |

---

## 八、技术实现亮点

1. **时间切分防泄漏**：严格使用 cutoff 前特征 + cutoff 后标签的构造方式，避免全周期建模中的时间泄漏问题。
2. **促销敏感度独立于 RFM**：将促销行为从价值分层中拆出，形成更可解释的二维策略矩阵（RFM 分段 × 促销敏感度）。
3. **First Observed Cohort 命名**：精确区分"数据集内首次出现"与"生命周期真实首购"，体现数据意识。
4. **SQL + Python 双实现**：核心分析在 Python 中实现，同时在 SQL 中提供了等效查询，展示多工具能力。
5. **相关性 ≠ 因果的边界意识**：整个项目反复强调因果推断需要实验数据支撑，这在初级分析师中难得。
6. **Synthetic Control 准实验扩展**：新增可运行 SCM 模块，将促销策略评估从描述性分析推进到反事实模拟和准 A/B 设计层面。

---

## 九、准因果延伸：Synthetic Control 作为促销策略准 A/B 评估

当前项目没有随机分组、实验批次或明确的发券策略变更字段，因此不能直接把促销码使用者与非使用者的差异解释为促销效果。促销码使用本身是客户选择、平台触达和客户活跃度共同作用的结果：高活跃客户更容易看到并使用促销码，低活跃客户也可能因为没有被触达而从未使用促销码。若直接把"用券客户"定义为 treatment，就会把自选择差异误认为策略效果。

Synthetic Control（合成控制法）更适合作为本项目的**准实验扩展工具**：当平台在某些客群或地区先行投放促销策略时，可以用未投放的相似单元构造反事实路径，比较投放后真实表现与 synthetic counterfactual 的差异。它不是随机 A/B test 的替代品，但可以在无法随机化或需要做小范围试点时，提供比简单前后对比更可信的评估框架。

### 9.1 已实现的面板设计

本项目已将 `segment × location × month` 作为 SCM 底层面板，而不是纯客户级或纯客群级：

- **不使用客户级 SCM**：单个客户的月度购买路径太稀疏，随机波动大，不适合构造稳定的合成控制。
- **不只使用客群级 SCM**：纯 `segment × month` 的供体数量太少，难以形成可靠 donor pool。
- **使用客群-地区-月份面板**：既保留 RFM 客群解释力，又利用 `Location` 扩展供体池，更适合做促销策略的准 A/B 评估。
- **防止分组泄漏**：SCM 的 segment 只用 `treatment_start` 之前的交易生成，不用处理后行为定义客群。

默认运行口径为：

```bash
python scripts/run_scm_analysis.py --input data/raw/EcommData_CSV.csv --treatment-start 2024-01-01 --outcome active_customer_rate
```

该命令生成 250 个 `segment × location` 单元，其中 73 个满足默认可行性条件。可行单元分布为：Dormant / Churn Risk 26 个、High Value 18 个、Potential Loyalist 17 个、Regular 12 个。

### 9.2 关键设计口径与输出

| 设计要素 | 推荐定义 | 说明 |
|---------|---------|------|
| Treatment unit | 默认自动选择可行性最高的 pseudo-treated unit | 本次为 `Dormant / Churn Risk | Montana` |
| Treatment time | `2024-01-01` | 该日期是模拟切点，不代表真实促销投放 |
| Donor pool | 同一 segment 的其他 location 单元 | 默认保持客群一致，只比较地区差异 |
| Outcome | `active_customer_rate` | 月活跃客户数 / 处理前该客群-地区客户数 |
| Predictors | 处理前 outcome path、orders per customer、sales per customer、promo usage rate | 核心目标是让 synthetic unit 在处理前尽量追踪 treated unit |

估计结果应呈现为处理后 gap 路径：

```text
gap_t = actual outcome_t - synthetic outcome_t
```

如果处理前拟合良好，而处理后 treated unit 的复购率或活跃率持续高于 synthetic unit，才可以谨慎表述为"该促销试点与更好的留存表现相一致"。若处理前拟合较差，则不应解读处理后 gap。

本次默认输出包括：

- `outputs/scm_panel.csv`
- `outputs/scm_feasibility_summary.csv`
- `outputs/scm_weights.csv`
- `outputs/scm_gap_path.csv`
- `outputs/scm_placebo_summary.csv`
- `outputs/scm_injected_lift_summary.csv`
- `outputs/scm_summary.csv`
- `outputs/scm_run_metadata.json`
- `figures/scm_actual_vs_synthetic.png`
- `figures/scm_gap_path.png`
- `figures/scm_placebo_mspe_ratio.png`
- `figures/scm_injected_lift_recovery.png`

### 9.3 SCM 运行结果

默认 pseudo-treated unit 为 `Dormant / Churn Risk | Montana`。处理前 24 个月、处理后 12 个月，结果如下：

| 指标 | 数值 |
|------|----:|
| Pre mean actual active rate | 23.96% |
| Post mean actual active rate | 37.24% |
| Pre mean gap | 1.13 pct. points |
| Post mean gap | 0.67 pct. points |
| Pre RMSE | 0.0420 |
| Post RMSE | 0.0911 |
| MSPE ratio | 4.71 |
| Placebo rank | 10 / 50 |
| Permutation-style p-value | 0.20 |

主要 donor weights 为：

| Donor unit | Weight |
|------------|------:|
| Dormant / Churn Risk \| Nevada | 19.02% |
| Dormant / Churn Risk \| South Dakota | 18.37% |
| Dormant / Churn Risk \| South Carolina | 13.00% |
| Dormant / Churn Risk \| New Hampshire | 12.24% |
| Dormant / Churn Risk \| Tennessee | 9.24% |
| Dormant / Churn Risk \| Arkansas | 8.15% |
| Dormant / Churn Risk \| Louisiana | 8.14% |
| Dormant / Churn Risk \| Michigan | 6.92% |
| Dormant / Churn Risk \| Arizona | 4.92% |

解读上，处理前拟合达到 `GOOD_PRE_FIT`，说明 SCM 可以为该 pseudo-treated unit 构造可用的合成路径。但处理后 gap 的平均值只有 0.67 个百分点，且 MSPE ratio 在 placebo 分布中排名第 10/50，经验 p-value 为 0.20。因此，这个默认模拟结果不支持把 Montana 的处理后变化解释为异常突出的策略效果；它更适合作为方法验证和报告展示样例。

### 9.4 Placebo 与 injected lift simulation

在没有真实实验分组前，本项目使用两类模拟检验 SCM 是否适合当前业务数据：

1. **Placebo backtest**：把同一 donor pool 中的每个地区轮流当作 pseudo-treated unit，检验真实 pseudo-treated unit 的 MSPE ratio 是否足够突出。本次 Montana 排名第 10/50，说明自然波动中也存在更大的 post/pre 偏离。
2. **Injected lift simulation**：在 post-period outcome 上人为加入 3%、5%、10% uplift。结果显示三个 uplift 的方向都被恢复，平均 recovery ratio 约为 1.00，说明该实现能识别被人工注入的正向变化。

### 9.5 可解释与不可解释边界

SCM 可以回答的问题是：在处理前路径相似的前提下，某个被投放策略的客群-地区单元，处理后的表现是否偏离了合成反事实路径。它适合用于评估地区试点、客群试点、分阶段上线策略和无法完全随机化的促销实验。

SCM 不能回答的问题是：当前历史数据中"使用过促销码"这一行为是否本身提高了留存。这个问题仍需要随机发券、严格 A/B test，或至少需要清晰的投放规则、触达记录和处理时间。因而，本项目的主结论仍保持为相关性分析；SCM 模块展示的是下一阶段准因果评估和实验设计能力。

---

## 十、局限性与改进方向

### 10.1 方法论局限

1. **RFM 评分阈值缺乏验证**：分位数评分 1-5 的切分及分段阈值（R≥4 等）未做敏感性分析，不同阈值可能导致不同的客户分布。
2. **促销敏感度阈值依赖样本分布**：75 分位数阈值是相对阈值，不同数据集会产生不同的分类结果，不利于跨时段或跨业务比较。
3. **队列留存存在右删失**：后期队列观测窗口短，热力图右下三角区域为不可观测数据，当前未做遮罩或标注处理。
4. **未做统计显著性检验**：促销 vs 非促销的 AOV 差异（USD 51.56 vs 51.93）未报告 t 检验或效应量，无法判断差异是否统计显著。
5. **单一模型**：只使用了 Random Forest，没有逻辑回归（可解释性 baseline）或规则模型（recency 阈值）作为对照。
6. **SCM 仍是准实验模拟**：虽然项目已实现 Synthetic Control、placebo test 和 injected lift simulation，但当前数据仍缺少真实投放时间、实验分组和触达记录，因此不能把默认 SCM 输出解释为已完成的促销效果评估。

### 10.2 后续改进方向

- 加入假设检验（t-test、Mann-Whitney U、chi-square）强化结论的统计严谨性
- 为不活跃模型添加 PR 曲线和阈值调优，找到业务最优的 precision-recall 平衡点
- 补充 CLV（客户生命周期价值）计算，将 RFM 分层与货币化价值关联
- 设计具体的 A/B 测试方案（样本量估算、随机化单位、评估指标、实验周期），并在无法完全随机化时使用 Synthetic Control 做准 A/B 反事实评估
- 引入 SHAP 值解读模型特征贡献，提供更丰富的业务洞察

---

## 十一、项目复现指南

### 环境要求

- Python ≥ 3.10
- 依赖：pandas、numpy、matplotlib、seaborn、scikit-learn、scipy、jupyter

### 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行完整分析（默认读取 data/raw/EcommData_CSV.csv）
python scripts/run_analysis.py

# 单独运行 SCM 准 A/B 扩展
python scripts/run_scm_analysis.py --input data/raw/EcommData_CSV.csv --treatment-start 2024-01-01 --outcome active_customer_rate

# 或在主流程中显式加入 SCM 扩展
python scripts/run_analysis.py --include-scm

# 生成 SQLite 数据库并运行 SQL 查询
python scripts/build_sqlite.py
sqlite3 data/processed/ecommerce.sqlite < sql/03_business_kpis.sql

# 运行测试
python -m unittest discover -s tests
```

### 输出文件

- `outputs/`：基础分析 CSV/JSON 文件，包含验证报告、月度 KPI、促销对比、队列留存、RFM 分层、模型指标及特征重要性
- `outputs/scm_*.csv` 与 `outputs/scm_run_metadata.json`：SCM 面板、可行性摘要、donor weights、gap path、placebo test、injected lift simulation 与运行元数据
- `figures/`：基础业务图表与 SCM 图表，包括 monthly trend、cohort heatmap、promo comparison、segment matrix、actual vs synthetic、gap path、placebo MSPE ratio 和 injected lift recovery

---

*本报告由 Claude Code 基于项目源代码与输出文件自动生成。项目地址：`ecommerce-promo-retention-analysis/`*
