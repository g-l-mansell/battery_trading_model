from datetime import datetime, date, timedelta, timezone
from enum import Enum

import pandas as pd
import plotly.express as px
import requests

from battery_trading_model.constants import DATA_DIR

import logging

logger = logging.getLogger(__name__)


ELEXON_API_URL = "https://data.elexon.co.uk/bmrs/api/v1"


class DataProvider(Enum):
    N2EX = "N2EXMIDP"
    APX = "APXMIDP"


def get_market_index_data(
    start_date: datetime, end_date: datetime, data_provider: DataProvider
) -> pd.DataFrame:
    # can only fetch 7 days of data at a time, so fetch in a loop and concatenate the results
    dfs = []
    n_days = (end_date - start_date).days
    for i in range(0, n_days, 7):
        current_start_date = start_date + timedelta(days=i)
        current_end_date = min(
            current_start_date + timedelta(days=7) - timedelta(minutes=30),
            end_date,
        )
        data = fetch_market_index_data(current_start_date, current_end_date, data_provider)
        df = format_market_index_response(data)
        dfs.append(df)
    all_data_df = pd.concat(dfs, ignore_index=True)
    all_data_df = order_df_by_datetime(all_data_df)
    return all_data_df


def fetch_market_index_data(
    start_date: datetime, end_date: datetime, data_provider: DataProvider
) -> dict:
    url = ELEXON_API_URL + "/balancing/pricing/market-index"
    payload = {
        "from": start_date.isoformat(),
        "to": end_date.isoformat(),
        "dataProviders": data_provider.value,
    }
    response = requests.get(url, params=payload)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(
            f"Failed to fetch Elexon market index data: {response.status_code} - {response.text}"
        )

def format_market_index_response(data: dict) -> pd.DataFrame:
    data = data.get("data")
    data = [{"datetime": d.get("startTime"), "price": d.get("price")} for d in data]
    df = pd.DataFrame(data)
    return df


def get_settlement_system_data(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    dfs = []
    n_days = (end_date - start_date).days
    single_date = start_date.date()
    for i in range(n_days):
        data = fetch_settlement_system_data(single_date)
        data = format_settlement_system_response(data)
        dfs.append(data)
        single_date += timedelta(days=1)
    all_data_df = pd.concat(dfs, ignore_index=True)
    all_data_df = order_df_by_datetime(all_data_df)
    return all_data_df


def fetch_settlement_system_data(
    date: date
) -> dict:
    url = ELEXON_API_URL + f"/balancing/settlement/system-prices/{date}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(
            f"Failed to fetch Elexon settlement system data: {response.status_code} - {response.text}"
        )

def format_settlement_system_response(data: dict) -> pd.DataFrame:
    data = data.get("data")
    data = [{"datetime": d.get("startTime"), "price": d.get("systemSellPrice")} for d in data]
    df = pd.DataFrame(data)
    return df


def order_df_by_datetime(df: pd.DataFrame) -> pd.DataFrame:
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)

    # check for duplicates
    if df["datetime"].duplicated().any():
        raise Exception("Duplicate datetime values found in dataframe")

    return df


def get_ons_data(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    df = fetch_ons_data()
    df = format_ons_data(df)
    df = df[(df["datetime"] >= start_date) & (df["datetime"] <= end_date)]
    return df


def fetch_ons_data() -> dict:
    excel_file_name = "electricitypricesdataset050226.xlsx"
    ONS_URL = "https://www.ons.gov.uk/file?uri=/economy/economicoutputandproductivity/output/datasets/systempriceofelectricity/2026"

    if (DATA_DIR / excel_file_name).exists():
        logger.info("ONS excel file already exists, skipping fetch")

    else:
        response = requests.get(f"{ONS_URL}/{excel_file_name}")

        if response.status_code == 200:
            with open(DATA_DIR / excel_file_name, "wb") as file:
                file.write(response.content)
        else:
            raise Exception(
                f"Failed to fetch ONS data: {response.status_code} - {response.text}"
            )
    
    data = pd.read_excel(DATA_DIR / excel_file_name, sheet_name="1.Daily SP Electricity", skiprows=4)
    return data


def format_ons_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={"Date": "datetime", "Daily average": "price"})
    df = df[["datetime", "price"]]
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


if __name__ == "__main__":

    start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)

    ### Get Market Index Data
    n2ex_file_name = DATA_DIR / "n2ex_data_2023.csv"
    apx_file_name = DATA_DIR / "apx_data_2023.csv"

    if n2ex_file_name.exists() and apx_file_name.exists():
        logger.info("Data files already exist, skipping fetch and loading from csv")
        n2ex_df = pd.read_csv(n2ex_file_name)
        apx_df = pd.read_csv(apx_file_name)

    else:
        logger.info("Fetching market index data...")
        n2ex_df = get_market_index_data(start_date, end_date, data_provider=DataProvider.N2EX)
        apx_df = get_market_index_data(start_date, end_date, data_provider=DataProvider.APX)

        n2ex_df.to_csv(n2ex_file_name, index=False)
        apx_df.to_csv(apx_file_name, index=False)

    # Looks like N2EX data is zero most of the time (not sure why?), lets use APX

    ### Get Settlement System Data
    ssp_file_name = DATA_DIR / "ssp_data_2023.csv"

    if ssp_file_name.exists():
        logger.info("Settlement system data file already exists, skipping fetch and loading from csv")
        ssp_df = pd.read_csv(ssp_file_name)
    else:
        logger.info("Fetching settlement system data...")
        ssp_df = get_settlement_system_data(start_date, end_date)
        ssp_df.to_csv(ssp_file_name, index=False)

    
    ### Get ONS Data
    ons_file_name = DATA_DIR / "ons_data_2023.csv"
    if ons_file_name.exists():
        logger.info("ONS data file already exists, skipping fetch and loading from csv")
        ons_df = pd.read_csv(ons_file_name)
    else:
        logger.info("Fetching ONS data...")
        ons_df = get_ons_data(start_date, end_date)
        ons_df.to_csv(ons_file_name, index=False)


    # quick look at some of the data
    fig = px.line(n2ex_df[0:1000], x="datetime", y="price", title="N2EX MID Price")
    fig.show()
    fig = px.line(apx_df[0:1000], x="datetime", y="price", title="APX MID Price")
    fig.show()
    fig = px.line(ssp_df[0:1000], x="datetime", y="price", title="Settlement System Price")
    fig.show()
    fig = px.line(ons_df, x="datetime", y="price", title="ONS Daily Average Price")
    fig.show()