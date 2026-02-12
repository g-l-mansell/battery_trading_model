from __future__ import annotations

from typing import Iterable

import pandas as pd
import plotly.express as px

from battery_trading_model.constants import DATA_DIR


PURCHASE_COLUMNS = ["Purchase from APX", "Purchase from SSP", "Purchase from ONS"]
SALE_COLUMNS = ["Sale to APX", "Sale to SSP", "Sale to ONS"]


def load_results(path=DATA_DIR / "result.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True)
    return df


def load_daily_summary(path=DATA_DIR / "daily_summary.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    return df


def _sum_columns(df: pd.DataFrame, columns: Iterable[str]) -> float:
    return float(df[list(columns)].sum().sum())


def _market_label(series: pd.Series) -> pd.Series:
    return series.str.replace("Purchase from ", "", regex=False).str.replace(
        "Sale to ", "", regex=False
    )


def plot_day_energy_stack(
    results: pd.DataFrame,
    day: str | pd.Timestamp,
    profit: float | None = None,
):
    df = results.copy()
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True)

    day_ts = pd.to_datetime(day).normalize()
    day_end = day_ts + pd.Timedelta(days=1)
    day_df = df[(df["Datetime"] >= day_ts) & (df["Datetime"] < day_end)].copy()

    if day_df.empty:
        raise ValueError("No data found for the requested day")

    purchased_total = _sum_columns(day_df, PURCHASE_COLUMNS)
    sold_total = _sum_columns(day_df, SALE_COLUMNS)

    purchases = day_df.melt(
        id_vars=["Datetime"],
        value_vars=PURCHASE_COLUMNS,
        var_name="Market",
        value_name="MWh",
    )
    purchases["Market"] = _market_label(purchases["Market"])
    purchases["Signed MWh"] = purchases["MWh"]

    sales = day_df.melt(
        id_vars=["Datetime"],
        value_vars=SALE_COLUMNS,
        var_name="Market",
        value_name="MWh",
    )
    sales["Market"] = _market_label(sales["Market"])
    sales["Signed MWh"] = -sales["MWh"]

    long_df = pd.concat([purchases, sales], ignore_index=True)

    profit_text = "n/a" if profit is None else f"{profit:,.2f}"
    day_label = day_ts.date().isoformat()
    title = (
        f"day {day_label}, purchased: {purchased_total:,.2f} MWh, "
        f"sold: {sold_total:,.2f} MWh, profit: £{profit_text}"
    )

    fig = px.bar(
        long_df,
        x="Datetime",
        y="Signed MWh",
        color="Market",
        title=title,
        labels={"Signed MWh": "Net energy (MWh)"},
    )
    fig.update_layout(barmode="relative")
    return fig


def plot_daily_profit(daily_summary: pd.DataFrame):
    df = daily_summary.copy()
    df["date"] = pd.to_datetime(df["date"])

    fig = px.line(
        df,
        x="date",
        y="profit",
        markers=True,
        title="Daily profit",
        labels={"profit": "Profit (£)", "date": "Date"},
    )
    return fig


def plot_net_power_heatmap(results: pd.DataFrame):
    df = results.copy()
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True)

    df["date"] = df["Datetime"].dt.date
    df["time"] = df["Datetime"].dt.strftime("%H:%M")

    purchases = df[PURCHASE_COLUMNS].sum(axis=1)
    sales = df[SALE_COLUMNS].sum(axis=1)
    df["net_mwh"] = purchases - sales

    heatmap_data = df.pivot(index="date", columns="time", values="net_mwh")

    fig = px.imshow(
        heatmap_data,
        aspect="auto",
        color_continuous_scale="RdBu",
        origin="lower",
        labels={"color": "Net energy (MWh)", "x": "Time", "y": "Day"},
        title="Net energy heatmap by time of day",
    )
    return fig


if __name__ == "__main__":
    results_df = load_results()
    first_day = results_df["Datetime"].min().normalize()
    daily_summary_df = load_daily_summary()

    profit_row = daily_summary_df[
        daily_summary_df["date"].dt.normalize() == first_day
    ]
    profit_value = float(profit_row["profit"].iloc[0])

    plot_day_energy_stack(results_df, day=first_day, profit=profit_value).show()

    plot_daily_profit(daily_summary_df).show()

    plot_net_power_heatmap(results_df).show()

