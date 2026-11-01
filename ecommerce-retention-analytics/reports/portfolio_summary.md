# Portfolio case study: e-commerce retention and revenue

## Executive summary

The cleaned dataset contains **1,067,371 source rows** across **2009-12-01 to 2011-12-09**. Under the documented positive-sale definition, it records **£20,476,260** across **40,077 orders** and **5,878 identified customers**. Returning customers represent **96.8%** of recorded sales among customers with an ID.

## Findings to validate with the dashboard

- **Geography:** United Kingdom is the largest country by recorded sales (£17,410,196).
- **Product:** Manual is the leading product by recorded sales (£339,226).
- **Customer segment:** Loyal contributes the largest segment-level customer revenue (£13,310,891).
- **Forecast baseline:** moving average 4w had the lower WAPE (18.4%) on a chronological holdout of 12 weeks.

## Recommended next actions

1. Treat the high-value / frequent customer segment as a retention hypothesis and test targeted reactivation or loyalty offers with a controlled experiment.
2. Review cancellation and return patterns before using gross recorded sales as a planning target.
3. Re-run the cohort and forecast analysis on recent first-party data before making present-day commercial decisions.

These are descriptive findings and test ideas. The dataset has no marketing exposure, margin, inventory, or experiment fields, so it cannot establish campaign causality, profitability, or current demand.

## Definitions and caveats

Recorded sales use positive quantity, positive unit price, and invoices not marked as cancellations. Returns and cancellations are excluded from positive sales and separately counted in `summary_metrics.json`. Missing customer IDs remain in sales totals but are excluded from customer metrics. This is historical data from one UK-based retailer; keep the UCI attribution and CC BY 4.0 license when sharing.
