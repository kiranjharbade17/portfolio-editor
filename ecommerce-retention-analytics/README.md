# E-commerce Customer Retention & Revenue Growth Analytics

An end-to-end analytics portfolio project built around a real transaction dataset. The project turns raw order-line data into a clean analytical dataset, customer and product insights, a retention view, an evaluation of a simple forecast, and an interactive dashboard.

## Business question

How can an online retailer understand its revenue quality, identify customer groups with different repeat-purchase patterns, and plan near-term demand?

## Dataset

**Online Retail II**, from the UCI Machine Learning Repository. It contains about 1.07 million transaction lines from a UK-based online retailer between December 2009 and December 2011. The downloadable source workbook is included at `data/raw/online_retail_ii.zip`.

- Source: <https://archive.ics.uci.edu/dataset/502/online%2Bretail%2Bii>
- Citation: Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D
- License: CC BY 4.0. Keep the attribution above when sharing derived work.
- The dataset is historical and from one retailer; results describe this dataset and should not be presented as current market benchmarks.

## Project questions

1. How do revenue, order volume, and average order value change by month and country?
2. How much revenue comes from first-time versus returning customers?
3. Which customer cohorts return, and how quickly does retention change over time?
4. Which customers and products contribute most to recorded sales?
5. How does a seasonal-naive weekly forecast compare with a four-week moving-average baseline on a chronological holdout?

## Methods

- Data quality audit, date and numeric parsing, duplicate removal, cancellation/return classification, and missing-customer treatment.
- Revenue reporting uses positive-quantity, positive-price, non-cancellation lines. Returns and cancellation lines are reported separately so they are not silently mixed into sales.
- Customer cohorts, repeat-customer revenue, RFM scoring, and transparent rule-based customer segments.
- Weekly forecasting with a time-ordered holdout, seasonal-naive baseline, moving-average comparator, MAE, and WAPE.
- PostgreSQL schema and business-question queries in `sql/`.

## Run it

1. Install Python 3.10+.
2. Open PowerShell in this folder and create a virtual environment: `py -m venv .venv`.
3. Activate it: `.\.venv\Scripts\Activate.ps1`.
4. Install dependencies: `python -m pip install -r requirements.txt`.
5. Run the analysis: `python src/analyze.py`.
6. Open `reports/dashboard.html` in a browser. The dashboard is self-contained and works offline.

The script reads the included ZIP, extracts the workbook when needed, and writes processed tables and report files. It can also be pointed at another copy of the workbook with `--input path/to/workbook.xlsx`.

To use the SQL examples, run the analysis first, create the table from `sql/01_schema.sql`, then import `data/processed/sales_lines.csv` into PostgreSQL using pgAdmin's Import/Export tool (CSV, header row on). Run the example questions from `sql/02_business_questions.sql`.

## Portfolio deliverables

- `reports/dashboard.html` — interactive overview of sales, customer mix, cohort retention, country performance, and forecast comparison.
- `reports/portfolio_summary.md` — concise, data-driven case study with findings, recommended next steps, and limitations.
- `reports/summary_metrics.json` — headline measures and forecast evaluation.
- `reports/*.csv` — reproducible metric tables, including cohorts and customer segments, for deeper exploration.
- `src/analyze.py` — end-to-end cleaning and analysis pipeline.
- `sql/` — PostgreSQL schema and reusable analysis queries.
- `tableau/TABLEAU_BUILD_GUIDE.md` — worksheet and dashboard plan using the exported CSVs.

## Metric definitions and caveats

- **Recorded sales** = quantity × unit price for positive-quantity, positive-price lines on invoices not marked as cancellations. This is not profit: cost and margin data are unavailable.
- **Order** = distinct non-cancellation invoice number among included sale lines.
- **Returning customer** = customer with at least two distinct included invoices in the full observed dataset. For predictive use, define this at a cutoff date to avoid using future behavior.
- **Cohort retention** = customers from a first-purchase month who made a purchase in a later month, divided by customers in that cohort's month zero.
- **WAPE** = sum of absolute forecast errors divided by sum of absolute actuals. It is undefined when the holdout actual total is zero.
- Rows without a customer ID remain available for sales reporting but are excluded from customer-level analysis.
- Cancellations, negative-quantity lines, and nonpositive-price lines are not counted as positive sales. Their counts and values are retained in the data-quality summary.
- Forecasting is deliberately evaluated on the final 12 observed weeks. It is a baseline exercise, not a production demand plan.

## Suggested interview walkthrough

Start with a business question, show how you defined sales and repeat customers, explain how you prevented future data from leaking into the forecast evaluation, then present one recommendation supported by a chart. Be ready to discuss missing customer IDs, cancellations, wholesale behavior, and the dataset's age.
