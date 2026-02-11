from battery_trading_model.constants import DATA_DIR, DEFAULT_BATTERY_PARAMETERS
from battery_trading_model.utils import save_model_results_to_excel
from pulp import makeDict, LpVariable, LpProblem, LpMaximize, lpSum, value, LpStatus
import pandas as pd
import logging

logger = logging.getLogger(__name__)


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

    # set up the pulp problem
    problem = LpProblem("Battery_Trading", LpMaximize) 

    # add the prices
    Markets = ["APX", "SSP"]
    Timepoints = list(range(48))
    SocTimepoints = list(range(49))
    P = [
        apx_day["price"].to_list(),
        ssp_day["price"].to_list(),
    ]
    P = makeDict([Markets, Timepoints], P)

    q = ons_day["price"].item()

    # add the decision variables
    X = LpVariable.dicts(
        "Half-hourly Purchases",
        (Markets, Timepoints),
        lowBound=0,
        upBound=DEFAULT_BATTERY_PARAMETERS.X_max,
        cat="Continuous",
    )
    Z = LpVariable.dicts(
        "Half-hourly Sales",
        (Markets, Timepoints),
        lowBound=0,
        upBound=DEFAULT_BATTERY_PARAMETERS.Z_max,
        cat="Continuous",
    )
    y = LpVariable(
        "Daily Purchases",
        lowBound=0,
        upBound=DEFAULT_BATTERY_PARAMETERS.y_max,
        cat="Continuous",
    )
    w = LpVariable(
        "Daily Sales",
        lowBound=0,
        upBound=DEFAULT_BATTERY_PARAMETERS.w_max,
        cat="Continuous",
    )
    SOC = LpVariable.dicts(
        "Battery State of Charge",
        SocTimepoints,
        lowBound=0,
        upBound=DEFAULT_BATTERY_PARAMETERS.C_max,
        cat="Continuous",
    )
    ChargeMode = LpVariable.dicts(
        "Charge Mode",
        Timepoints,
        cat="Binary",
    )

    # add the objective function
    problem += (
        q * (w - y)
        + lpSum([P[m][t] * (Z[m][t] - X[m][t]) for m in Markets for t in Timepoints]),
        "Profit_ObjectiveFunction",
    )

    # add the SOC constraints
    problem += SOC[0] == 0, "SOC_initial_0"
    for t in Timepoints:
        problem += (
            lpSum([X[m][t] for m in Markets]) + y / 48
            <= DEFAULT_BATTERY_PARAMETERS.X_max * ChargeMode[t],
            f"Charge_limit_{t}",
        )
        problem += (
            lpSum([Z[m][t] for m in Markets]) + w / 48
            <= DEFAULT_BATTERY_PARAMETERS.Z_max * (1 - ChargeMode[t]),
            f"Discharge_limit_{t}",
        )
        problem += (
            SOC[t + 1]
            == SOC[t]
            + (
                DEFAULT_BATTERY_PARAMETERS.frac_charged
                * (
                    X["APX"][t]
                    + X["SSP"][t]
                    + y / 48
                )
            )
            - (
                DEFAULT_BATTERY_PARAMETERS.frac_discharged
                * (
                    Z["APX"][t]
                    + Z["SSP"][t]
                    + w / 48
                )
            ),
            f"SOC_update_{t}",
        )

    # run the optimisation
    logger.info("Solving the optimization problem...")
    problem.solve()
    logger.info("Status: %s", LpStatus[problem.status])

    save_model_results_to_excel(X=X, Z=Z, y=y, w=w, SOC=SOC, path=DATA_DIR / "result.csv")