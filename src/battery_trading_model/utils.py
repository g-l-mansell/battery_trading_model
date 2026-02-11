import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def save_model_results_to_excel(
    X: dict, Z: dict, y: float, w: float, SOC: dict, path: Path
) -> None:
    logger.info("Converting model results to dataframe.")

    # convert results to dfs and save
    y_res = y.varValue
    w_res = w.varValue
    SOC_res = []
    X1_res = []
    X2_res = []
    X3_res = []
    Z1_res = []
    Z2_res = []
    Z3_res = []

    Timepoints = X["APX"].keys()
    for t in Timepoints:
        SOC_res.append(SOC[t].varValue)
        X1_res.append(X["APX"][t].varValue)
        X2_res.append(X["SSP"][t].varValue)

        Z1_res.append(Z["APX"][t].varValue)
        Z2_res.append(Z["SSP"][t].varValue)

        X3_res.append(y_res / 48)
        Z3_res.append(w_res / 48)

    df = pd.DataFrame(
        data={
            "Datetime": Timepoints,
            "SOC": SOC_res,
            "Purchase from APX": X1_res,
            "Purchase from SSP": X2_res,
            "Purchase from ONS": X3_res,
            "Sale to APX": Z1_res,
            "Sale to SSP": Z2_res,
            "Sale to ONS": Z3_res,
        }
    )

    final_timepoint = list(SOC.keys())[-1]
    final_soc = SOC[final_timepoint].varValue
    df.loc[len(df)] = {
        "Datetime": final_timepoint,
        "SOC": final_soc
    }

    df.to_csv(path, index=False)
    logger.info(f"Model results saved to {path}")
