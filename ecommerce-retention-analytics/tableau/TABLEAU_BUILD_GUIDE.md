# Tableau Public build guide

The analysis exports Tableau-ready CSVs to `reports/`. Connect each CSV as a text-file data source and build the sheets below. Save the workbook locally in this project folder as `tableau/ecommerce_retention_growth.twbx`.

## Suggested sheets

1. **Monthly sales** — `monthly_revenue.csv`; plot `Revenue` by `InvoiceMonth`, with `Orders` and `AverageOrderValue` available for tooltips. Sort `InvoiceMonth` ascending.
2. **Customer revenue mix** — `customer_revenue_mix.csv`; stacked bars by `InvoiceMonth`, colored by `CustomerType`.
3. **Cohort retention** — `cohort_retention.csv`; use Tableau's Pivot on the `Month_0`, `Month_1`, … columns to create a long table with `MonthIndex` and `Retention`. Build a highlight table with cohort month as rows and month index as columns.
4. **Country performance** — `country_performance.csv`; horizontal bars by `Revenue`, with `Orders` and `Customers` in tooltips.
5. **Customer segments** — `segment_performance.csv`; compare `Customers` and `SalesGBP` by `Segment`.
6. **Forecast holdout** — `forecast_holdout.csv`; pivot `SeasonalNaiveForecast` and `MovingAverageForecast` into forecast type/value fields, then plot both with `Revenue` by `Week`.

## Dashboard layout

Place monthly sales and customer mix across the top, cohort retention in the center, and country performance plus segment mix across the bottom. Add date and country filters where relevant. Label all money values as GBP and include the dataset's 2009–2011 date range and historical-data caveat in a footer.

## Data sources

- `reports/monthly_revenue.csv`
- `reports/customer_revenue_mix.csv`
- `reports/cohort_retention.csv`
- `reports/country_performance.csv`
- `reports/segment_performance.csv`
- `reports/forecast_holdout.csv`

Keep the UCI attribution and CC BY 4.0 note from the main README when sharing the workbook.
