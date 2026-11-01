"""Build the cleaned tables and portfolio dashboard for Online Retail II."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "reports"


def get_input_path(user_input: str | None) -> Path:
    if user_input:
        path = Path(user_input).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")
        return path
    for candidate in sorted(RAW_DIR.rglob("*.xlsx")):
        return candidate
    archives = list(RAW_DIR.glob("*.zip"))
    if not archives:
        raise FileNotFoundError("No .xlsx workbook or .zip archive found under data/raw")
    extracted_dir = RAW_DIR / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archives[0]) as archive:
        workbook_names = [name for name in archive.namelist() if name.lower().endswith(".xlsx")]
        if not workbook_names:
            raise FileNotFoundError("The ZIP archive does not contain an .xlsx workbook")
        for name in workbook_names:
            archive.extract(name, extracted_dir)
    return next(extracted_dir.rglob("*.xlsx"))


def load_workbook(path: Path) -> pd.DataFrame:
    sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    frames = []
    for sheet_name, frame in sheets.items():
        frame = frame.copy()
        frame["SourceSheet"] = str(sheet_name)
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    data.columns = [str(col).strip() for col in data.columns]
    aliases = {
        "Invoice": "InvoiceNo",
        "InvoiceNo": "InvoiceNo",
        "StockCode": "StockCode",
        "Description": "Description",
        "Quantity": "Quantity",
        "InvoiceDate": "InvoiceDate",
        "Price": "UnitPrice",
        "UnitPrice": "UnitPrice",
        "Customer ID": "CustomerID",
        "CustomerID": "CustomerID",
        "Country": "Country",
    }
    data = data.rename(columns={col: aliases[col] for col in data.columns if col in aliases})
    required = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise ValueError(f"Workbook is missing expected columns: {missing}")
    data = data[required + ["SourceSheet"]]
    data["InvoiceNo"] = data["InvoiceNo"].astype("string").str.strip()
    data["StockCode"] = data["StockCode"].astype("string").str.strip()
    data["CustomerID"] = data["CustomerID"].astype("string").str.replace(r"\.0$", "", regex=True).str.strip()
    data["Country"] = data["Country"].astype("string").str.strip()
    data["Description"] = data["Description"].astype("string").str.strip()
    data["InvoiceDate"] = pd.to_datetime(data["InvoiceDate"], errors="coerce")
    data["Quantity"] = pd.to_numeric(data["Quantity"], errors="coerce")
    data["UnitPrice"] = pd.to_numeric(data["UnitPrice"], errors="coerce")
    data["GrossLineValue"] = data["Quantity"] * data["UnitPrice"]
    data["IsCancellation"] = data["InvoiceNo"].str.upper().str.startswith("C", na=False)
    data["IsReturnLine"] = (~data["IsCancellation"]) & (data["Quantity"] < 0)
    data["IsValidSale"] = (
        (~data["IsCancellation"])
        & (data["Quantity"] > 0)
        & (data["UnitPrice"] > 0)
        & data["InvoiceDate"].notna()
    )
    data["SalesValue"] = data["GrossLineValue"].where(data["IsValidSale"], 0.0)
    data["InvoiceMonth"] = data["InvoiceDate"].dt.to_period("M").astype("string")
    data["InvoiceWeek"] = data["InvoiceDate"].dt.to_period("W-SUN").dt.start_time
    return data


def customer_tables(sales: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    customer_sales = sales.dropna(subset=["CustomerID"]).copy()
    order_rows = customer_sales[["CustomerID", "InvoiceNo", "InvoiceDate", "SalesValue"]]
    orders = order_rows.groupby(["CustomerID", "InvoiceNo"], as_index=False).agg(
        OrderDate=("InvoiceDate", "min"), OrderValue=("SalesValue", "sum")
    )
    max_date = sales["InvoiceDate"].max().normalize()
    ref_date = max_date + pd.Timedelta(days=1)
    rfm = orders.groupby("CustomerID").agg(
        RecencyDays=("OrderDate", lambda x: int((ref_date - x.max().normalize()).days)),
        Frequency=("InvoiceNo", "nunique"),
        Monetary=("OrderValue", "sum"),
        FirstOrderDate=("OrderDate", "min"),
        LastOrderDate=("OrderDate", "max"),
    ).reset_index()
    rfm = rfm[rfm["Monetary"] > 0].copy()
    rfm["RecencyScore"] = pd.qcut(rfm["RecencyDays"].rank(method="first"), 4, labels=[4, 3, 2, 1]).astype(int)
    rfm["FrequencyScore"] = pd.qcut(rfm["Frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["MonetaryScore"] = pd.qcut(rfm["Monetary"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["RFMScore"] = rfm[["RecencyScore", "FrequencyScore", "MonetaryScore"]].astype(str).agg("".join, axis=1)
    rfm["Segment"] = "Needs attention"
    rfm.loc[(rfm["RecencyScore"] >= 3) & (rfm["FrequencyScore"] >= 3), "Segment"] = "Loyal"
    rfm.loc[(rfm["RecencyScore"] == 4) & (rfm["FrequencyScore"] <= 2), "Segment"] = "Recent customers"
    rfm.loc[(rfm["RecencyScore"] <= 2) & (rfm["FrequencyScore"] >= 3), "Segment"] = "At risk, previously frequent"
    rfm.loc[(rfm["RecencyScore"] <= 2) & (rfm["FrequencyScore"] <= 2), "Segment"] = "Lapsed"

    first_order = orders.groupby("CustomerID")["OrderDate"].min().rename("FirstOrderDate")
    orders = orders.join(first_order, on="CustomerID", rsuffix="_cohort")
    orders["CohortMonth"] = orders["FirstOrderDate"].dt.to_period("M")
    orders["OrderMonth"] = orders["OrderDate"].dt.to_period("M")
    orders["CohortIndex"] = (orders["OrderMonth"].dt.year - orders["CohortMonth"].dt.year) * 12 + (orders["OrderMonth"].dt.month - orders["CohortMonth"].dt.month)
    cohort_counts = orders.groupby(["CohortMonth", "CohortIndex"])["CustomerID"].nunique().unstack(fill_value=0)
    cohort_size = cohort_counts.iloc[:, 0]
    retention = cohort_counts.divide(cohort_size, axis=0)
    retention.index = retention.index.astype(str)
    retention.columns = [f"Month_{int(col)}" for col in retention.columns]
    retention.index.name = "CohortMonth"
    return rfm, retention.reset_index(), orders


def forecast_weekly(weekly: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    values = weekly.sort_values("Week").reset_index(drop=True).copy()
    holdout = min(12, max(4, len(values) // 8))
    split = max(1, len(values) - holdout)
    train = values.iloc[:split].copy()
    test = values.iloc[split:].copy()
    forecasts = []
    history = train["Revenue"].tolist()
    for week in test["Week"]:
        moving = sum(history[-4:]) / min(4, len(history))
        seasonal = history[-52] if len(history) >= 52 else moving
        forecasts.append((week, seasonal, moving))
        history.append(float(values.loc[values["Week"] == week, "Revenue"].iloc[0]))
    result = test.merge(pd.DataFrame(forecasts, columns=["Week", "SeasonalNaiveForecast", "MovingAverageForecast"]), on="Week", how="left")
    actual = result["Revenue"].abs().sum()
    metrics = {}
    for name, column in [("seasonal_naive", "SeasonalNaiveForecast"), ("moving_average_4w", "MovingAverageForecast")]:
        errors = (result["Revenue"] - result[column]).abs()
        metrics[name] = {
            "mae": float(errors.mean()),
            "wape": float(errors.sum() / actual) if actual else None,
        }
    return result, {"holdout_weeks": int(len(result)), "metrics": metrics}


def build_dashboard(monthly: pd.DataFrame, mix: pd.DataFrame, retention: pd.DataFrame, country: pd.DataFrame, forecast: pd.DataFrame, metrics: dict) -> None:
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=("Monthly sales", "First-time vs returning customer sales", "Cohort retention", "Top countries by sales"),
        specs=[[{"type": "scatter"}, {"type": "bar"}], [{"type": "heatmap", "colspan": 2}, None], [{"type": "bar", "colspan": 2}, None]],
        vertical_spacing=0.14,
    )
    fig.add_trace(go.Scatter(x=monthly["InvoiceMonth"], y=monthly["Revenue"], mode="lines+markers", name="Sales"), row=1, col=1)
    for label in mix["CustomerType"].drop_duplicates():
        subset = mix[mix["CustomerType"] == label]
        fig.add_trace(go.Bar(x=subset["InvoiceMonth"], y=subset["Revenue"], name=label), row=1, col=2)
    cohort_cols = [col for col in retention.columns if col.startswith("Month_")]
    heat = retention.set_index("CohortMonth")[cohort_cols]
    fig.add_trace(go.Heatmap(z=heat.values * 100, x=cohort_cols, y=heat.index, colorscale="Blues", colorbar={"title": "Retained %"}, zmin=0, zmax=100), row=2, col=1)
    top_country = country.head(12).sort_values("Revenue")
    fig.add_trace(go.Bar(x=top_country["Revenue"], y=top_country["Country"], orientation="h", name="Sales by country", marker_color="#247ba0"), row=3, col=1)
    fig.update_layout(title="E-commerce Customer Retention & Revenue Growth", template="plotly_white", height=1200, barmode="stack", legend={"orientation": "h", "y": 1.06})
    # Add forecast comparison as a standalone figure below the main dashboard.
    forecast_fig = go.Figure()
    forecast_fig.add_trace(go.Scatter(x=forecast["Week"], y=forecast["Revenue"], mode="lines+markers", name="Actual"))
    forecast_fig.add_trace(go.Scatter(x=forecast["Week"], y=forecast["SeasonalNaiveForecast"], mode="lines+markers", name="Seasonal naive"))
    forecast_fig.add_trace(go.Scatter(x=forecast["Week"], y=forecast["MovingAverageForecast"], mode="lines+markers", name="4-week average"))
    forecast_fig.update_layout(title=f"Weekly forecast holdout — {metrics['holdout_weeks']} weeks", template="plotly_white", height=380)
    headline = f"""<section class="kpis"><div><b>Sales lines</b><strong>{metrics['sale_lines']:,}</strong></div><div><b>Recorded sales</b><strong>£{metrics['recorded_sales']:,.0f}</strong></div><div><b>Orders</b><strong>{metrics['orders']:,}</strong></div><div><b>Known customers</b><strong>{metrics['customers']:,}</strong></div><div><b>Repeat customer sales</b><strong>{metrics['repeat_sales_share']:.1%}</strong></div></section>"""
    body = fig.to_html(full_html=False, include_plotlyjs=True) + forecast_fig.to_html(full_html=False, include_plotlyjs=False)
    note = "<p class='note'>Sales are positive-quantity, positive-price, non-cancellation line values in GBP. Returns and cancellations are excluded from sales and summarized separately. Dataset: UCI Online Retail II; historical single-retailer data.</p>"
    html = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Retail Retention Analytics</title><style>body{{font-family:Inter,Segoe UI,Arial,sans-serif;max-width:1250px;margin:32px auto;padding:0 18px;color:#152238;background:#f7f9fc}}h1{{margin-bottom:4px}}.sub,.note{{color:#536273}}.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:22px 0}}.kpis div{{background:#fff;border:1px solid #dce4ee;border-radius:12px;padding:16px}}.kpis b,.kpis strong{{display:block}}.kpis b{{font-size:13px;color:#526579;margin-bottom:7px}}.kpis strong{{font-size:23px}}.note{{font-size:13px;line-height:1.55}}.chart{{background:#fff;border-radius:12px;padding:12px;margin:16px 0}}</style></head><body><h1>E-commerce Customer Retention &amp; Revenue Growth</h1><p class="sub">Portfolio analysis of transaction quality, repeat buying, customer cohorts, geography, and a weekly forecast baseline.</p>{headline}<div class="chart">{body}</div>{note}<p class="note">For full metric definitions and caveats, see README.md.</p></body></html>"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "dashboard.html").write_text(html, encoding="utf-8")


def build_portfolio_summary(metrics: dict, country: pd.DataFrame, products: pd.DataFrame, segments: pd.DataFrame) -> None:
    best_forecast = min(metrics["forecast"]["metrics"], key=lambda key: metrics["forecast"]["metrics"][key]["wape"] or float("inf"))
    best_wape = metrics["forecast"]["metrics"][best_forecast]["wape"]
    top_country = country.iloc[0]
    top_product = products.iloc[0]
    top_segment = segments.sort_values("SalesGBP", ascending=False).iloc[0]
    summary = f"""# Portfolio case study: e-commerce retention and revenue

## Executive summary

The cleaned dataset contains **{metrics['raw_rows']:,} source rows** across **{metrics['date_min']} to {metrics['date_max']}**. Under the documented positive-sale definition, it records **£{metrics['recorded_sales']:,.0f}** across **{metrics['orders']:,} orders** and **{metrics['customers']:,} identified customers**. Returning customers represent **{metrics['repeat_sales_share']:.1%}** of recorded sales among customers with an ID.

## Findings to validate with the dashboard

- **Geography:** {top_country['Country']} is the largest country by recorded sales (£{top_country['Revenue']:,.0f}).
- **Product:** {top_product['Description']} is the leading product by recorded sales (£{top_product['Revenue']:,.0f}).
- **Customer segment:** {top_segment['Segment']} contributes the largest segment-level customer revenue (£{top_segment['SalesGBP']:,.0f}).
- **Forecast baseline:** {best_forecast.replace('_', ' ')} had the lower WAPE ({best_wape:.1%}) on a chronological holdout of {metrics['forecast']['holdout_weeks']} weeks.

## Recommended next actions

1. Treat the high-value / frequent customer segment as a retention hypothesis and test targeted reactivation or loyalty offers with a controlled experiment.
2. Review cancellation and return patterns before using gross recorded sales as a planning target.
3. Re-run the cohort and forecast analysis on recent first-party data before making present-day commercial decisions.

These are descriptive findings and test ideas. The dataset has no marketing exposure, margin, inventory, or experiment fields, so it cannot establish campaign causality, profitability, or current demand.

## Definitions and caveats

Recorded sales use positive quantity, positive unit price, and invoices not marked as cancellations. Returns and cancellations are excluded from positive sales and separately counted in `summary_metrics.json`. Missing customer IDs remain in sales totals but are excluded from customer metrics. This is historical data from one UK-based retailer; keep the UCI attribution and CC BY 4.0 license when sharing.
"""
    (REPORT_DIR / "portfolio_summary.md").write_text(summary, encoding="utf-8")


def run(input_arg: str | None) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = get_input_path(input_arg)
    raw = load_workbook(path)
    duplicate_count = int(raw.duplicated(subset=["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]).sum())
    clean = raw.drop_duplicates(subset=["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]).copy()
    sale = clean[clean["IsValidSale"]].copy()
    sale["CustomerType"] = "Unidentified customer"
    known = sale.dropna(subset=["CustomerID"])
    first_invoice = (
        known[["CustomerID", "InvoiceNo", "InvoiceDate"]]
        .drop_duplicates()
        .sort_values(["CustomerID", "InvoiceDate", "InvoiceNo"])
        .drop_duplicates("CustomerID")
        .set_index("CustomerID")["InvoiceNo"]
    )
    sale.loc[known.index, "CustomerType"] = "Returning"
    is_first_invoice = sale["InvoiceNo"].eq(sale["CustomerID"].map(first_invoice))
    sale.loc[is_first_invoice, "CustomerType"] = "First-time"

    monthly = sale.groupby("InvoiceMonth", as_index=False).agg(Revenue=("SalesValue", "sum"), Orders=("InvoiceNo", "nunique"), Customers=("CustomerID", "nunique"))
    monthly["AverageOrderValue"] = monthly["Revenue"] / monthly["Orders"].replace(0, pd.NA)
    monthly.to_csv(REPORT_DIR / "monthly_revenue.csv", index=False)
    mix = sale.groupby(["InvoiceMonth", "CustomerType"], as_index=False)["SalesValue"].sum().rename(columns={"SalesValue": "Revenue"})
    mix.to_csv(REPORT_DIR / "customer_revenue_mix.csv", index=False)
    country = sale.groupby("Country", as_index=False).agg(Revenue=("SalesValue", "sum"), Orders=("InvoiceNo", "nunique"), Customers=("CustomerID", "nunique"), Units=("Quantity", "sum")).sort_values("Revenue", ascending=False)
    country.to_csv(REPORT_DIR / "country_performance.csv", index=False)
    products = sale.groupby(["StockCode", "Description"], as_index=False).agg(Revenue=("SalesValue", "sum"), Units=("Quantity", "sum"), Orders=("InvoiceNo", "nunique")).sort_values("Revenue", ascending=False)
    products.head(100).to_csv(REPORT_DIR / "top_products.csv", index=False)
    weekly = sale.groupby("InvoiceWeek", as_index=False).agg(Revenue=("SalesValue", "sum"), Orders=("InvoiceNo", "nunique"))
    weekly = weekly.rename(columns={"InvoiceWeek": "Week"})
    forecast, forecast_metrics = forecast_weekly(weekly)
    forecast.to_csv(REPORT_DIR / "forecast_holdout.csv", index=False)
    rfm, retention, orders = customer_tables(sale)
    rfm.to_csv(REPORT_DIR / "customer_rfm_segments.csv", index=False)
    retention.to_csv(REPORT_DIR / "cohort_retention.csv", index=False)
    segments = rfm.groupby("Segment", as_index=False).agg(Customers=("CustomerID", "nunique"), SalesGBP=("Monetary", "sum"), MedianOrders=("Frequency", "median")).sort_values("SalesGBP", ascending=False)
    segments.to_csv(REPORT_DIR / "segment_performance.csv", index=False)
    sale.to_csv(PROCESSED_DIR / "sales_lines.csv", index=False)

    customer_revenue = sale[sale["CustomerID"].notna()].groupby("CustomerID").agg(Revenue=("SalesValue", "sum"), Orders=("InvoiceNo", "nunique"))
    repeat_customers = int((customer_revenue["Orders"] >= 2).sum())
    eligible_sales = float(customer_revenue["Revenue"].sum())
    repeat_sales = float(customer_revenue.loc[customer_revenue["Orders"] >= 2, "Revenue"].sum())
    metrics = {
        "dataset": "UCI Online Retail II",
        "input_file": str(path.name),
        "date_min": str(clean["InvoiceDate"].min().date()),
        "date_max": str(clean["InvoiceDate"].max().date()),
        "raw_rows": int(len(raw)),
        "duplicate_rows_removed": duplicate_count,
        "sale_lines": int(len(sale)),
        "cancellation_lines": int(clean["IsCancellation"].sum()),
        "return_lines": int(clean["IsReturnLine"].sum()),
        "missing_customer_id_lines": int(clean["CustomerID"].isna().sum()),
        "recorded_sales": float(sale["SalesValue"].sum()),
        "orders": int(sale["InvoiceNo"].nunique()),
        "customers": int(sale["CustomerID"].nunique()),
        "repeat_customers": repeat_customers,
        "repeat_sales_share": (repeat_sales / eligible_sales) if eligible_sales else 0.0,
        "forecast": forecast_metrics,
    }
    (REPORT_DIR / "summary_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    build_dashboard(monthly, mix, retention, country, forecast, {**metrics, **forecast_metrics})
    build_portfolio_summary(metrics, country, products, segments)
    print(f"Analysis complete. Dashboard: {REPORT_DIR / 'dashboard.html'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="Optional path to an Online Retail II Excel workbook")
    args = parser.parse_args()
    run(args.input)


if __name__ == "__main__":
    main()
