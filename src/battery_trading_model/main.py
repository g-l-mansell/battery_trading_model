import logging

import pandas as pd

from battery_trading_model.constants import DATA_DIR
from battery_trading_model.model import build_problem
from battery_trading_model.solver import evaluate_profit, solve_problem
from battery_trading_model.utils import save_model_results_to_excel

logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def filter_data_by_day(df: pd.DataFrame, day: pd.Timestamp) -> pd.DataFrame:
    df["datetime"] = pd.to_datetime(df["datetime"])
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

def estimate_final_soc_value(apx_day: pd.DataFrame, ssp_day: pd.DataFrame, ons_day:pd.DataFrame) -> float:
    total_prices = sum(apx_day["price"]) + sum(ssp_day["price"]) + ons_day["price"].item()*48
    return total_prices / (len(apx_day) + len(ssp_day) + 48)

if __name__ == "__main__":

    test_day = pd.Timestamp(2023, 1, 1, tz="UTC")

    # load the price data
    apx_data = pd.read_csv(DATA_DIR / "apx_data_2023.csv") # half hourly
    ssp_data = pd.read_csv(DATA_DIR / "ssp_data_2023.csv") # half hourly
    ons_data = pd.read_csv(DATA_DIR / "ons_data_2023.csv") # daily

    apx_day = filter_data_by_day(apx_data, test_day)
    ssp_day = filter_data_by_day(ssp_data, test_day)
    ons_day = filter_data_by_day(ons_data, test_day)

    # run checks
    check_data(apx_day, ssp_day, ons_day)

    final_soc_value = estimate_final_soc_value(apx_day, ssp_day, ons_day)
    problem, model = build_problem(
        apx_prices=apx_day["price"].to_list(),
        ssp_prices=ssp_day["price"].to_list(),
        daily_price=ons_day["price"].item(),
        final_soc_value=final_soc_value,
    )

    logger.info("Solving the optimization problem...")
    status, objective_value = solve_problem(problem)
    logger.info(f"Status: {status}")

    total_profit = evaluate_profit(
        P=model["P"],
        q=model["q"],
        X=model["X"],
        Z=model["Z"],
        y=model["y"],
        w=model["w"],
    )
    logger.info(f"Estimated profit: {total_profit}")
    logger.info(f"Theoretical profit from objective function: {objective_value}")

    save_model_results_to_excel(
        X=model["X"],
        Z=model["Z"],
        y=model["y"],
        w=model["w"],
        SOC=model["SOC"],
        path=DATA_DIR / "result.csv",
    )