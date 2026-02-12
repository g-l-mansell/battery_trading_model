from pulp import LpVariable, LpProblem, LpMaximize, lpSum, makeDict

from battery_trading_model.constants import DEFAULT_BATTERY_PARAMETERS, BatteryParameters


def build_problem(
    apx_prices: list[float],
    ssp_prices: list[float],
    daily_price: float,
    final_soc_price: float,
    initial_soc: float,
    battery_params: BatteryParameters = DEFAULT_BATTERY_PARAMETERS,
) -> tuple[LpProblem, dict]:

    problem = LpProblem("Battery_Trading", LpMaximize)

    n_timepoints = len(apx_prices)
    timepoints = list(range(n_timepoints))
    soc_timepoints = list(range(n_timepoints+1))
    markets = ["APX", "SSP"]

    prices = makeDict([markets, timepoints], [apx_prices, ssp_prices])
    q = daily_price

    X = LpVariable.dicts(
        "Half-hourly Purchases",
        (markets, timepoints),
        lowBound=0,
        upBound=battery_params.X_max,
        cat="Continuous",
    )
    Z = LpVariable.dicts(
        "Half-hourly Sales",
        (markets, timepoints),
        lowBound=0,
        upBound=battery_params.Z_max,
        cat="Continuous",
    )
    y = LpVariable(
        "Daily Purchases",
        lowBound=0,
        upBound=battery_params.y_max,
        cat="Continuous",
    )
    w = LpVariable(
        "Daily Sales",
        lowBound=0,
        upBound=battery_params.w_max,
        cat="Continuous",
    )
    SOC = LpVariable.dicts(
        "Battery State of Charge",
        soc_timepoints,
        lowBound=0,
        upBound=battery_params.C_max,
        cat="Continuous",
    )
    charge_mode = LpVariable.dicts(
        "Charge Mode",
        timepoints,
        cat="Binary",
    )

    problem += (
        q * (w - y)
        + lpSum([prices[m][t] * (Z[m][t] - X[m][t]) for m in markets for t in timepoints])
        + final_soc_price * SOC[soc_timepoints[-1]],
        "ObjectiveFunction",
    )

    problem += SOC[0] == initial_soc, "SOC_initial"
    for t in timepoints:
        # update SOC based on previous SOC, purchases, and sales 
        problem += (
            SOC[t+1]
            == SOC[t]
            + (
                battery_params.frac_charged
                * (
                    X["APX"][t]
                    + X["SSP"][t]
                    + y / n_timepoints
                )
            )
            - (
                battery_params.frac_discharged
                * (
                    Z["APX"][t]
                    + Z["SSP"][t]
                    + w / n_timepoints
                )
            ),
            f"SOC_update_{t}",
        )
        # enforce charging and discharging limits
        problem += (
            lpSum([X[m][t] for m in markets]) + y / n_timepoints
            <= battery_params.X_max * charge_mode[t],
            f"Charge_limit_{t}",
        )
        problem += (
            lpSum([Z[m][t] for m in markets]) + w / n_timepoints
            <= battery_params.Z_max * (1 - charge_mode[t]),
            f"Discharge_limit_{t}",
        )

    model = {
        "P": prices,
        "q": q,
        "X": X,
        "Z": Z,
        "y": y,
        "w": w,
        "SOC": SOC,
        "markets": markets,
        "timepoints": timepoints,
    }
    return problem, model
