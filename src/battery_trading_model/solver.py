from pulp import LpProblem, LpStatus, LpVariable, value


def solve_problem(problem: LpProblem) -> tuple[str, float]:
    problem.solve()
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
