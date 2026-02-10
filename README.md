# Battery Trading Model

## Set up
This repo has been set up using Docker to manage dependencies. 

Run the following command to build the Docker image:
```
docker build -t battery_trading_model .
```
Then to run the Docker container:
```
docker run -p 8888:8888 battery_trading_model notebook
```

To run the jupyter notebook in VS Code within the container, copy the url printed in the terminal, open the notebook, select kernel, select existing jupyter server, and paste the url.

This repo also uses pre-commit to autoformat the code using `ruff`. To configure, run
```
pip install pre-commit
pre-commit install
```


## Optimisation Problem

We have 3 energy markets (m=1, 2, 3), the first two are half-hourly markets (with T timepoints) and the third is a daily market (with D days).

### Parameters

We have the following parameters for the battery's charge:
- `C_max`: Maximum capacity (MWh)
- `c_rate`: Charging rate (MW)
- `d_rate`: Discharging rate (MW)
- `c_efficiency`: Charging efficiency (fraction of energy lost)
- `d_efficiency`: Discharging efficiency (fraction of energy lost)

For its lifetime:
- `max_lifetime`: Maximum lifetime (years)
- `max_cycles`: Maximum charging cycles (number)
- `degredation_rate`: Capacity lost per cycle (%/cycle)

And for its costs:
- `capex`: Initial cost ($)
- `opex`: Fixed annual cost ($/year)

### Decision Variables
Let:
- X = a 2xT matrix of the amount of energy purchased from markets 1 and 2
- y = a D-length vector of the amount of energy purchased from market 3
- Z = a 2xT matrix of the amount of energy sold to markets 1 and 2
- w = a D-length vector of the amount of energy sold to market 3
- P = a 2xT matrix of the energy prices in markets 1 and 2
- q = a D-length vector of the energy prices in market 3

Relationship between the two market types:
- There are 48 timepoints in each day (`T=48*D`)
- To participate in the daily market, we decide amount at the first time point in the day
- So at time point t, we need to know the corresponding day d
  - `d = ceiling(t/48)` if t is an int `d=date(t)` if t is a datetime
- Then the energy is transferred equally throughout the day
- So at time point t the amount purchased = `y_{d}/48`

Impact of charging efficiencies
- When we buy 1 MWh from any market, we loose a certain fraction before it reaches the battery, so we only gain `frac_charged = 1-c_efficiency` in the SoC.
- When we sell 1 MWh to any market, we need to discharge `frac_discharged = 1/(1-d_efficiency)` MWh from the battery to get 1 MWh to the market.

(Not sure about my assumption here; we have to cover the losses both ways?)

At time t, the battery's state of charge (SOC) is given by:
```math
SOC_{t} = SOC_{t-1} + f_{c} (X_{1,t} + X_{2,t} + y_{d}/48) - f_{d} (Z_{1,t} + Z_{2,t} + w_{d}/48)
```

### Objective Function
We want to optimise the profit from the battery trading, given by:
```math
Profit = \sum_{t=1}^{T} \sum_{m=1}^{2} P_{m,t} (Z_{m,t} - X_{m,t}) + \sum_{d=1}^{D} q_{d}(w_{d} - y_{d})
```

### Constraints

The battery's SOC must be within its capacity limits at all times:
```math
0 \leq SOC_{t} \leq C_{max}
```

The amount of energy bought/sold must be within the batteries charging/discharging limits:

$$0 \leq X_{m,t} \leq c_{rate} * 0.5$$

$$0 \leq Z_{m,t} \leq d_{rate} * 0.5$$

$$0 \leq y_{d} \leq c_{rate} * 24$$

$$0 \leq w_{d} \leq d_{rate} * 24$$


### Limitations
- The charging limits should probably interact e.g. you can only charge or discharge at any point in time, max rate is split between markets
- This does not currently take into account the battery's degradation
- This model is purely backwards looking: what are the best decisions trades we could have made given all 3 years of data. A more realistic model would e.g. a day ahead only.
- To avoid complete decharging at the last timepoint, we could alter the objective function to give a value to any remaining charge.