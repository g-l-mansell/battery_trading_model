import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def filter_data_by_day(df: pd.DataFrame, day: pd.Timestamp) -> pd.DataFrame:
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    day_end = day + pd.Timedelta(days=1)
    return df[(day <= df["datetime"]) & (df["datetime"] < day_end)]


def check_data(apx_day: pd.DataFrame, ssp_day: pd.DataFrame, ons_day: pd.DataFrame) -> None:
    for df in [apx_day, ssp_day]:
        if len(df) != 48:
            raise ValueError(f"Expected 48 half-hourly data points, but got {len(df)}")
    if len(ons_day) != 1:
        raise ValueError(f"Expected 1 daily data point, but got {len(ons_day)}")
    if not apx_day["datetime"].equals(ssp_day["datetime"]):
        raise ValueError("APX and SSP data have different datetime values")


def get_avg_daily_price(apx_day: pd.DataFrame, ssp_day: pd.DataFrame, ons_day:pd.DataFrame) -> float:
    total_prices = sum(apx_day["price"]) + sum(ssp_day["price"]) + ons_day["price"].item()*48
    return total_prices / (len(apx_day) + len(ssp_day) + 48)


def build_model_results_dataframe(
    X: dict,
    Z: dict,
    y: float,
    w: float,
    SOC: dict,
    timepoints: list[pd.Timestamp],
) -> pd.DataFrame:
    logger.info("Converting model results to dataframe.")

    y_res = y.varValue
    w_res = w.varValue
    SOC_res = []
    X1_res = []
    X2_res = []
    X3_res = []
    Z1_res = []
    Z2_res = []
    Z3_res = []

    for i, t in enumerate(timepoints):
        SOC_res.append(SOC[i].varValue)
        X1_res.append(X["APX"][i].varValue)
        X2_res.append(X["SSP"][i].varValue)

        Z1_res.append(Z["APX"][i].varValue)
        Z2_res.append(Z["SSP"][i].varValue)

        X3_res.append(y_res / len(timepoints))
        Z3_res.append(w_res / len(timepoints))

    df = pd.DataFrame(
        data={
            "Datetime": timepoints,
            "SOC": SOC_res,
            "Purchase from APX": X1_res,
            "Purchase from SSP": X2_res,
            "Purchase from ONS": X3_res,
            "Sale to APX": Z1_res,
            "Sale to SSP": Z2_res,
            "Sale to ONS": Z3_res,
        }
    )

    return df


def save_model_results(
    daily_results: list[pd.DataFrame],
    path: Path,
) -> None:
    df = pd.concat(daily_results, ignore_index=True)
    df.to_csv(path, index=False)
    logger.info(f"Model results saved to {path}")
