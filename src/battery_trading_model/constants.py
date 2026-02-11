from dataclasses import dataclass
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"


@dataclass
class BatteryParameters:
    C_max: float
    c_rate: float
    d_rate: float
    c_efficiency: float
    d_efficiency: float
    max_lifetime: int
    max_cycles: int
    capex: int
    opex: int

    @property
    def X_max(self):
        return self.c_rate * 0.5

    @property
    def Z_max(self):
        return self.d_rate * 0.5

    @property
    def y_max(self):
        return self.c_rate * 24

    @property
    def w_max(self):
        return self.d_rate * 24

    @property
    def frac_charged(self):
        return 1 - self.c_efficiency

    @property
    def frac_discharged(self):
        return 1 / (1 - self.d_efficiency)


# initalise a battery with parameters from the BEIS 2018 report
DEFAULT_BATTERY_PARAMETERS = BatteryParameters(
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