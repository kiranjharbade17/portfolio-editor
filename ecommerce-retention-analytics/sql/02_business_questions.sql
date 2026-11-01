-- Monthly sales, order volume, and average order value
SELECT date_trunc('month', InvoiceDate)::date AS month,
       SUM(SalesValue) AS recorded_sales_gbp,
       COUNT(DISTINCT InvoiceNo) AS orders,
       SUM(SalesValue) / NULLIF(COUNT(DISTINCT InvoiceNo), 0) AS average_order_value_gbp
FROM retail_sales_lines
WHERE IsValidSale
GROUP BY 1
ORDER BY 1;

-- Country performance (interpret smaller markets with care)
SELECT Country,
       SUM(SalesValue) AS recorded_sales_gbp,
       COUNT(DISTINCT InvoiceNo) AS orders,
       COUNT(DISTINCT CustomerID) AS known_customers
FROM retail_sales_lines
WHERE IsValidSale
GROUP BY Country
ORDER BY recorded_sales_gbp DESC
LIMIT 20;

-- Product performance
SELECT StockCode, MAX(Description) AS product,
       SUM(SalesValue) AS recorded_sales_gbp,
       SUM(Quantity) AS units,
       COUNT(DISTINCT InvoiceNo) AS orders
FROM retail_sales_lines
WHERE IsValidSale
GROUP BY StockCode
ORDER BY recorded_sales_gbp DESC
LIMIT 25;

-- Repeat customer sales share; use a cutoff-date version for any predictive exercise.
WITH customer_orders AS (
    SELECT CustomerID, COUNT(DISTINCT InvoiceNo) AS order_count,
           SUM(SalesValue) AS customer_sales
    FROM retail_sales_lines
    WHERE IsValidSale AND CustomerID IS NOT NULL
    GROUP BY CustomerID
)
SELECT SUM(customer_sales) FILTER (WHERE order_count >= 2)
         / NULLIF(SUM(customer_sales), 0) AS repeat_customer_sales_share
FROM customer_orders;

-- Customer-level RFM inputs; score and segment with documented thresholds in Python.
SELECT CustomerID,
       (MAX(InvoiceDate)::date) AS last_order_date,
       COUNT(DISTINCT InvoiceNo) AS frequency,
       SUM(SalesValue) AS monetary_gbp
FROM retail_sales_lines
WHERE IsValidSale AND CustomerID IS NOT NULL
GROUP BY CustomerID;

-- Cohort retention by month since first purchase.
WITH customer_first_month AS (
    SELECT CustomerID, MIN(date_trunc('month', InvoiceDate)) AS cohort_month
    FROM retail_sales_lines
    WHERE IsValidSale AND CustomerID IS NOT NULL
    GROUP BY CustomerID
), customer_active_months AS (
    SELECT DISTINCT t.CustomerID, f.cohort_month,
           date_trunc('month', t.InvoiceDate) AS order_month,
           ((EXTRACT(YEAR FROM date_trunc('month', t.InvoiceDate)) - EXTRACT(YEAR FROM f.cohort_month)) * 12
             + EXTRACT(MONTH FROM date_trunc('month', t.InvoiceDate)) - EXTRACT(MONTH FROM f.cohort_month))::int AS month_index
    FROM retail_sales_lines t
    JOIN customer_first_month f USING (CustomerID)
    WHERE t.IsValidSale
)
SELECT cohort_month::date AS cohort_month, month_index,
       COUNT(DISTINCT CustomerID) AS active_customers,
       COUNT(DISTINCT CustomerID)::numeric
         / NULLIF(FIRST_VALUE(COUNT(DISTINCT CustomerID)) OVER (PARTITION BY cohort_month ORDER BY month_index), 0) AS retention_rate
FROM customer_active_months
GROUP BY cohort_month, month_index
ORDER BY cohort_month, month_index;

-- Cancellations and return lines are reported separately from sales.
SELECT COUNT(*) FILTER (WHERE IsCancellation) AS cancellation_lines,
       COUNT(*) FILTER (WHERE IsReturnLine) AS return_lines,
       SUM(ABS(GrossLineValue)) FILTER (WHERE IsCancellation) AS cancellation_value_gbp,
       SUM(ABS(GrossLineValue)) FILTER (WHERE IsReturnLine) AS return_value_gbp
FROM retail_sales_lines;
