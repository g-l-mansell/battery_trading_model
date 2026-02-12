# Battery Trading Model

This python project aims to simulate energy trading from a battery storage system. 

Assume we have access to a battery (properties described below), and the ability to participate in different electricity markets. We want to create a trading system that will decide which actions to take in order to maximise profit from the battery. 

We can fetch electricity prices from three data sources:
1. Market index data from [Elexon](https://bmrs.elexon.co.uk/api-documentation/endpoint/balancing/pricing/market-index)
2. Settlement system sale prices from [Elexon](https://bmrs.elexon.co.uk/api-documentation/endpoint/balancing/settlement/system-prices/%7BsettlementDate%7D)
3. System price of electricity from [the Office of National Statistics](https://www.ons.gov.uk/economy/economicoutputandproductivity/output/datasets/systempriceofelectricity)

Datasources 1 and 2 are half hourly prices, and 3 is daily prices. Let's assume that these are three energy markets (m=1,2,3) in which we can participate, and all prices are released one day-ahead. 

Once we have the day-ahead prices, we choose at each timepoint whether to purchase electricity from one of the markets (charging our battery), sell to one of the markets (discharging our battery), or to do nothing (keep the current state of charge). 

We can formulate this as an optimisation problem, using the package `PuLP`. 

### Battery properties

We have the following parameters for the battery's charge:
- `C_max`: Maximum capacity (MWh)
- `c_rate`: Charging rate (MW)
- `d_rate`: Discharging rate (MW)
- `c_efficiency`: Charging efficiency (fraction of energy lost)
- `d_efficiency`: Discharging efficiency (fraction of energy lost)

For its lifetime:
- `max_lifetime`: Maximum lifetime (years)
- `max_cycles`: Maximum charging cycles (number)

And for its costs:
- `capex`: Initial cost ($)
- `opex`: Fixed annual cost ($/year)

For this excerise, we assume our battery has the properties listed in [BEIS 2018 report, Table 7 New Battery Storage FM Data](https://assets.publishing.service.gov.uk/media/5f3cf6c9d3bf7f1b0fa7a165/storage-costs-technical-assumptions-2018.pdf)

### Optimisation problem

Each day there are 48 timepoints to make decisions for the half-hourly markets (T=48), and 1 timepoint to make decisions for the daily market (D=1).

Let:
- `P`: a 2xT matrix of the energy prices in markets 1 and 2
- `q`: the energy prices in market 3

Our decision variables are:
- `X`: a 2xT matrix of the amount of energy purchased from markets 1 and 2
- `y`: the amount of energy purchased from market 3
- `Z`: a 2xT matrix of the amount of energy sold to markets 1 and 2
- `w`: the amount of energy sold to market 3

We assume that to participate in the daily market, we must transfer energy equally throughout the day, so at time point `t` the amount of energy purchased from market 3 is `y/48` (and `w/48` for energy sold)

Impact of charging efficiencies
- When we buy 1 MWh from any market, we loose a certain fraction before it reaches the battery, so we only gain `frac_charged = 1-c_efficiency`.
- When we sell 1 MWh to any market, we need to discharge `frac_discharged = 1/(1-d_efficiency)` MWh from the battery to get 1 MWh to the market.

At time t, the battery's state of charge (SOC) is given by:
```math
SOC_{t} = SOC_{t-1} + f_{c} (X_{1,t} + X_{2,t} + y/48) - f_{d} (Z_{1,t} + Z_{2,t} + w/48)
```
We use 49 SOC points (t=0..48) for 48 half-hourly intervals so every interval updates SOC once.

### Objective Function
We want to optimise the profit from the battery trading, given by:
```math
Profit = \sum_{t=1}^{T} \sum_{m=1}^{2} P_{m,t} (Z_{m,t} - X_{m,t}) + q(w - y)
```

However this optimisation optimisation will always choose to fully discharge by the end of the day, which may not be optimal in a longer term strategy. To counteract this we can put a estimated value on the final charge $v$ e.g. the average price of the current day. 

This gives us an objective function which differs slightly from the profit calculation.

```math
Objective function = \sum_{t=1}^{T} \sum_{m=1}^{2} P_{m,t} (Z_{m,t} - X_{m,t}) + q(w - y) + v \cdot SOC_{T}
```

### Constraints

The battery's SOC must be within its capacity limits at all times:
```math
0 \leq SOC_{t} \leq C_{max}
```

The amount of energy traded must be possible given the battery's charging/discharging rates. If we were only participating in a single market at a time, the total energy transfered (MWh) must be less than the rate (MW) multiplied by the number of hours (h) i.e.

$$0 \leq X_{m,t} \leq c_{rate} * 0.5$$

$$0 \leq Z_{m,t} \leq d_{rate} * 0.5$$

$$0 \leq y \leq c_{rate} * 24$$

$$0 \leq w \leq d_{rate} * 24$$

Assuming the battery cannot be charging and discharging at the same time, we can add a binary variable at each time point: `Mode=1` for charging and `Mode=0` for discharging. The total energy transfered at each timepoint must also match the charging rates.

So we can construct the following two constraints, where the value of `Mode` "turns on" one of the constraints, and "turns off" the other (because the constraint becomes `<=0`).

$$X_{1,t} + X_{2,t} + y/48 \leq c_{rate} * 0.5 * \text{Mode}_{t}$$

$$Z_{1,t} + Z_{2,t} + w/48 \leq d_{rate} * 0.5 * (1 - \text{Mode}_{t})$$



### Todos
- Add tests
- Add set up description and instructions to the top of the readme
- Add a cost to each cycle (since it counts towards the total number of lifetime cycles)
- Run for the whole year and compare profit to opex+capex (Note for 1 day it takes about 3 seconds to run, so for a year it will take about 18 minutes)
- Improve the data visualisations
- Investigate why the daily market is never used
