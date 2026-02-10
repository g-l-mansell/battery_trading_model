from dataclasses import dataclass

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
