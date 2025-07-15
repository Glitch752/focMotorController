class IDController:
    """
    PI controller for d-axis and q-axis currents.
    """
    kp: float
    ki: float
    int: float

    def __init__(self, kp: float, ki: float):
        self.kp = kp
        self.ki = ki
        self.int = 0

    def reset(self):
        self.int = 0.0

    def compute(self, error: float, dt: float) -> float:
        self.int += error * self.ki * dt
        return self.kp * error + self.int