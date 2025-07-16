import math
from ..motor_sim import SimIOInterface
from . import MotorController

class SixStepController(MotorController):
    io: SimIOInterface
    
    def __init__(self, io: SimIOInterface):
        self.io = io
    
    def reset(self):
        pass
    
    @staticmethod
    def get_commutation_state(progress: float) -> bool:
        while progress <= 0:
            progress += 1
        while progress > 1:
            progress -= 1
        return progress >= 0.5

    def get_phase_voltages(self, dt: float) -> tuple[float, float, float]:
        theta = self.io.get_encoder_position()
        electrical_angle = self.io.motor.properties.mechanical_to_electrical_angle(theta)
        progress: float = electrical_angle % (2 * math.pi) / (2 * math.pi)

        phase_advance = 0.9 # Proportion of a cycle (0 to 1)

        return (
            self.get_commutation_state(progress + phase_advance) * 12,
            self.get_commutation_state(progress + phase_advance - 1/3) * 12,
            self.get_commutation_state(progress + phase_advance - 2/3) * 12
        )