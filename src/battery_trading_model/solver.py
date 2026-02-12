from pulp import LpProblem, LpStatus, LpVariable, value, PULP_CBC_CMD


def solve_problem(problem: LpProblem) -> tuple[str, float]:
    problem.solve(PULP_CBC_CMD(msg=0))
    status = LpStatus[problem.status]
    objective_value = value(problem.objective)
    return status, objective_value


def evaluate_profit(
    P: dict,
    q: float,
    X: dict,
    Z: dict,
    y: LpVariable,
    w: LpVariable,
) -> float:
    half_hourly_profit = sum(
        P[m][t] * (Z[m][t].varValue - X[m][t].varValue)
        for m in P
        for t in P[m]
    )
    daily_profit = q * (w.varValue - y.varValue)
    return half_hourly_profit + daily_profit


def get_final_soc(SOC: dict) -> float: 
    max_key = max(SOC.keys())
    return SOC[max_key].varValue