from abc import ABC, abstractmethod
from ..motor_sim import SimIOInterface

class MotorController(ABC):
    @abstractmethod
    def __init__(self, io: SimIOInterface):
        pass
    
    @abstractmethod
    def get_phase_voltages(self, dt: float) -> tuple[float, float, float]:
        pass
    
    @abstractmethod
    def reset(self):
        pass