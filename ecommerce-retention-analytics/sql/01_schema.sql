-- PostgreSQL staging table for data/processed/sales_lines.csv.
-- The Python pipeline creates the cleaned CSV before this table is populated.
CREATE TABLE IF NOT EXISTS retail_sales_lines (
    InvoiceNo       TEXT,
    StockCode       TEXT,
    Description     TEXT,
    Quantity        NUMERIC,
    InvoiceDate     TIMESTAMP,
    UnitPrice       NUMERIC(12, 4),
    CustomerID      TEXT,
    Country         TEXT,
    SourceSheet     TEXT,
    GrossLineValue  NUMERIC(14, 4),
    IsCancellation BOOLEAN,
    IsReturnLine    BOOLEAN,
    IsValidSale     BOOLEAN,
    SalesValue      NUMERIC(14, 4),
    InvoiceMonth    TEXT,
    InvoiceWeek     TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_retail_sales_date ON retail_sales_lines (InvoiceDate);
CREATE INDEX IF NOT EXISTS idx_retail_sales_customer ON retail_sales_lines (CustomerID);
CREATE INDEX IF NOT EXISTS idx_retail_sales_invoice ON retail_sales_lines (InvoiceNo);
