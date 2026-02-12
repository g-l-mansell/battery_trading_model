import logging

import pandas as pd

from battery_trading_model.constants import DATA_DIR
from battery_trading_model.model import build_problem
from battery_trading_model.solver import evaluate_profit, solve_problem, get_final_soc
from battery_trading_model.utils import build_model_results_dataframe, filter_data_by_day, get_avg_daily_price, check_data, save_model_results

logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


if __name__ == "__main__":

    # load the price data
    apx_data = pd.read_csv(DATA_DIR / "apx_data_2023.csv") # half hourly
    ssp_data = pd.read_csv(DATA_DIR / "ssp_data_2023.csv") # half hourly
    ons_data = pd.read_csv(DATA_DIR / "ons_data_2023.csv") # daily

    start_day = pd.to_datetime(apx_data["datetime"]).min().normalize()
    num_days = 5
    start_of_day_soc = 0  # first day will start at 0, but will be updated each day

    daily_profits: list[float] = []
    daily_objectives: list[float] = []
    daily_results: list[pd.DataFrame] = []
    end_of_day_soc: list[float] = []

    for day_offset in range(num_days):

        day = start_day + pd.Timedelta(days=day_offset)

        logger.info(f"Processing data for {day}...")

        apx_day = filter_data_by_day(apx_data, day)
        ssp_day = filter_data_by_day(ssp_data, day)
        ons_day = filter_data_by_day(ons_data, day)

        check_data(apx_day, ssp_day, ons_day)
        final_soc_price = get_avg_daily_price(apx_day, ssp_day, ons_day)
        timepoints = apx_day["datetime"].to_list()

        problem, model = build_problem(
            apx_prices=apx_day["price"].to_list(),
            ssp_prices=ssp_day["price"].to_list(),
            daily_price=ons_day["price"].item(),
            final_soc_price=final_soc_price,
            initial_soc=start_of_day_soc,
        )

        logger.info(f"Solving the optimization problem for {day.date()}...")
        status, objective_value = solve_problem(problem)
        logger.info(f"Status: {status}")

        daily_profit = evaluate_profit(
            P=model["P"],
            q=model["q"],
            X=model["X"],
            Z=model["Z"],
            y=model["y"],
            w=model["w"],
        )
        daily_profits.append(daily_profit)
        daily_objectives.append(objective_value)
        logger.info(f"Estimated profit: {daily_profit}")
        logger.info(f"Objective value (inc theoritical price of remaining SOC): {objective_value}")

        results_df = build_model_results_dataframe(
            X=model["X"],
            Z=model["Z"],
            y=model["y"],
            w=model["w"],
            SOC=model["SOC"],
            timepoints=timepoints,
        )
        daily_results.append(results_df)

        final_soc = get_final_soc(model["SOC"])
        initial_soc = final_soc

    output_path = DATA_DIR / "result.csv"
    save_model_results(daily_results=daily_results, path=output_path)

    logger.info(f"Total profit over {num_days} days: {sum(daily_profits)}")