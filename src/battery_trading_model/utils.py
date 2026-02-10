import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def load_daily_prices(path: Path) -> pd.DataFrame:
    logger.info(f"Loading daily prices from {path}")
    df = pd.read_excel(path, sheet_name="Daily data")
    df = df.rename(columns={"Unnamed: 0": "Date"})
    df["Date"] = df["Date"].dt.date
    return df


def load_half_hourly_prices(path: Path) -> pd.DataFrame:
    logger.info(f"Loading half hourly prices from {path}")
    df = pd.read_excel(path, sheet_name="Half-hourly data")
    df = df.rename(columns={"Unnamed: 0": "Datetime"})
    df["Datetime"] = pd.to_datetime(df["Datetime"])
    df = fix_duplicated_timestamps(df)
    return df


def fix_duplicated_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """There are some duplicate datetimes in the half hourly price data at 2am and 2:30am
    in March each year, 1am and 1:30 am are missing - probably related to clocks changing."""

    error_rows = df[
        df.duplicated(subset=["Datetime"], keep="last")
    ]  # find the indexes of the first copy
    for index in error_rows.index:
        df.loc[index, "Datetime"] = df.loc[index, "Datetime"] - pd.Timedelta(
            hours=1
        )  # subtract 1 hr
    return df


def save_model_results_to_excel(
    X: dict, Z: dict, y: dict, w: dict, SOC: dict, path: Path
) -> None:
    logger.info("Converting model results to dataframe.")

    # convert results to dfs and save
    y_res = []
    w_res = []
    SOC_res = []
    X1_res = []
    X2_res = []
    X3_res = []
    Z1_res = []
    Z2_res = []
    Z3_res = []

    for d in y.keys():
        y_d = y[d].varValue
        w_d = w[d].varValue

        y_res.append(y_d)
        w_res.append(w_d)

        X3_res += [y_d / 48] * 48
        Z3_res += [w_d / 48] * 48

    for t in SOC.keys():
        SOC_res.append(SOC[t].varValue)
        X1_res.append(X["Market1"][t].varValue)
        X2_res.append(X["Market2"][t].varValue)
        Z1_res.append(Z["Market1"][t].varValue)
        Z2_res.append(Z["Market2"][t].varValue)

    df = pd.DataFrame(
        data={
            "Datetime": SOC.keys(),
            "SOC": SOC_res,
            "Purchase from Market 1": X1_res,
            "Purchase from Market 2": X2_res,
            "Purchase from Market 3": X3_res,
            "Sale to Market 1": Z1_res,
            "Sale to Market 2": Z2_res,
            "Sale to Market 3": Z3_res,
        }
    )
    with pd.ExcelWriter(path) as writer:
        df.to_excel(writer, sheet_name="results")

    logger.info(f"Model results saved to {path}")
