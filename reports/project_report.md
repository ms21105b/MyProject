# E-commerce Promo Retention Analysis Report

## Executive Summary

- Dataset: 102,771 orders from 3,900 customers, covering 2022-01-01 to 2024-12-31.
- Promo-code orders account for 13.19% of all orders.
- Promo-code AOV is USD 51.56 vs USD 51.93 for non-promo orders, so promo usage is not a clear high-AOV signal in this dataset.
- No Promo customers have the highest observed future inactivity risk: 35.01% in the 2024-06-30 snapshot.
- The time-split 180-day inactivity model reaches ROC-AUC 0.912 on the 2023-12-31 test snapshot, with recall 0.808 and precision 0.238 for inactive customers.
- The Synthetic Control extension runs a pseudo-treatment quasi A/B simulation for `Dormant / Churn Risk | Montana`: pre-fit is labeled `GOOD_PRE_FIT`, but the placebo rank is 10/50 with p-value 0.20, so it is a method demonstration rather than a causal promo-effect claim.

## Method Notes

- Cohort analysis uses first observed purchase month inside this dataset, not lifetime first purchase.
- Promo sensitivity is separated from RFM segmentation:
  - No Promo: no observed promo-code usage.
  - Moderate Promo: promo user below the promo-user 75th percentile usage rate.
  - High Promo: promo user at or above the promo-user 75th percentile usage rate.
- Future inactivity risk is built with cutoff-safe snapshots: historical features before cutoff, labels from the following 180 days.
- All promo findings are correlational and do not identify causal effects.
- Synthetic Control uses a cutoff-safe `segment × location × month` panel, convex donor weights, placebo MSPE ratios, and injected lift simulation. Current SCM outputs are quasi A/B simulations because the raw data has no randomized treatment assignment or real promo rollout date.

## Recommended Actions

- Use High Value and Potential Loyalist segments for retention and loyalty benefits rather than broad discounts.
- Prioritize Dormant / Churn Risk customers for low-cost reactivation.
- Test introductory low-friction incentives for No Promo customers, whose future inactivity risk is highest.
- Use the inactivity model as a prioritization screen, not an automated decision system, because its inactive-class precision is limited.
