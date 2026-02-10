

from battery_trading_model.constants import BatteryParameters


if __name__ == "__main__":

    # initalise battery parameters
    # Source: BEIS 2018 report, Table 7 New Battery Storage FM Data
    # https://assets.publishing.service.gov.uk/media/5f3cf6c9d3bf7f1b0fa7a165/storage-costs-technical-assumptions-2018.pdf
    battery_params = BatteryParameters(
        C_max=50, 
        c_rate=50, 
        d_rate=50, 
        c_efficiency=0.05,
        d_efficiency=0.05,
        max_lifetime=15,
        max_cycles=1500,
        capex=118_717_286,
        opex=1_335_001, 
    )