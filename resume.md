# Resume Materials

## 中文简历 Bullet

- 使用 SQL 与 Python 分析 102,771 条、覆盖 2022-2024 年的电商订单数据，完成分号分隔、逗号小数和 0/1 标签等真实数据清洗，并构建月度 GMV、AOV、促销码使用率和客户活跃指标。
- 基于 first observed cohort retention 与 RFM 分位数打分完成 3,900 名客户分层，并将促销敏感度拆分为 No Promo、Moderate Promo、High Promo，用于设计差异化促销策略。
- 构建 180 天未来不活跃风险模型，使用 `2023-06-30` 训练快照和 `2023-12-31` 测试快照，避免使用全周期行为特征造成时间泄漏。
- 实现 Synthetic Control 准 A/B 扩展，基于 cutoff-safe 的 `segment × location × month` 面板生成 donor weights、gap path、placebo test 和 injected lift simulation，用于反事实评估促销试点。
- 对促销码订单与非促销码订单进行 AOV、历史购买次数和 `Churn` 标签对比，明确区分相关性发现与因果推断边界。

## English Resume Bullets

- Analyzed 102,771 ecommerce orders from 2022-2024 with SQL and Python, cleaning real-world CSV formats and building KPI views for GMV, AOV, promo-code usage, and active customers.
- Built first-observed cohort retention and RFM segmentation for 3,900 customers, separating promo sensitivity into No Promo, Moderate Promo, and High Promo tiers for targeted promotion strategies.
- Developed a 180-day future inactivity risk model using time-based snapshots (`2023-06-30` train cutoff and `2023-12-31` test cutoff) to avoid full-period feature leakage.
- Implemented a Synthetic Control quasi A/B extension with cutoff-safe segment-location-month panels, donor weights, placebo tests, and injected-lift simulations for counterfactual promo evaluation.
- Compared promo-code and non-promo order behavior across AOV, prior purchases, and churn labels while explicitly separating correlation from causal claims.

## 60-Second Project Pitch

我做了一个电商促销码与用户留存分析项目，目标是回答“促销码使用行为和用户复购、留存、未来不活跃风险之间有什么关系，以及平台应该怎样做分层促销”。项目使用 102,771 条真实订单和 3,900 名客户数据，覆盖 2022-2024 年。我用 Python 处理了分号分隔、逗号小数和 0/1 标签等真实数据清洗问题，用 SQL 和 Python 构建月度销售、客单价、促销码使用率、first observed cohort 留存和 RFM 分层。之后我把促销敏感度作为独立维度，区分 No Promo、Moderate Promo 和 High Promo，并用时间切分方式构建未来 180 天不活跃风险模型，避免全周期模型的时间泄漏。为了进一步展示准因果思维，我还实现了 Synthetic Control 扩展，用 cutoff-safe 的客群-地区-月份面板做 pseudo-treatment、placebo test 和 injected lift simulation。整个项目里我特别注意没有把相关性或准实验模拟说成因果，因为数据没有随机发券或真实 A/B 测试字段。

## Interview Q&A

**Q: 为什么不能说促销码提升了留存？**
A: 因为数据里没有随机发券、实验组或准实验变量，促销码使用可能和用户本身价格敏感度、购买意愿、品类偏好有关。我只能说明促销码使用与订单行为、留存或流失标签之间存在相关性，不能直接做因果结论。

**Q: Synthetic Control 在这个项目里做了什么？**
A: 我用 `segment × location × month` 构建了 cutoff-safe 面板，默认以 2024-01-01 作为 pseudo-treatment 切点，为一个客群-地区单元构造 synthetic counterfactual，并输出 donor weights、gap path、placebo MSPE ratio 和 injected lift recovery。因为没有真实投放记录，这部分是准 A/B 方法验证，不是促销效果证明。

**Q: 为什么 cohort 叫 first observed cohort？**
A: 因为 `Previous Purchases` 显示客户在数据窗口前已经有购买历史，所以数据集内最早订单不一定是生命周期首购。我把它定义为 first observed purchase cohort，避免把观测窗口内首次出现误说成真实首购。

**Q: 为什么要做时间切分的不活跃模型？**
A: 如果用 2022-2024 全周期行为预测同一全周期的 churn，会把未来行为放进特征里，造成时间泄漏。所以我用 cutoff 前行为生成特征，再用 cutoff 后 180 天是否无购买生成标签。

**Q: 促销码分析的核心发现是什么？**
A: 促销码覆盖客户很广，3,476/3,900 个客户至少使用过一次，但促销码订单只占 13.19%。同时促销码订单 AOV 与非促销码订单 AOV 很接近，所以不应简单认为促销码带来了更高客单价。

**Q: 这个项目最能体现你的什么能力？**
A: 一是 SQL 和 Python 的端到端分析能力，二是处理真实数据格式和验证口径的能力，三是把数据指标转化成业务策略的能力，四是对分析边界的判断，比如避免时间泄漏和区分相关性与因果。
