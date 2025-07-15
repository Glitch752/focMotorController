import math
from typing import cast

from ..util import clamp

from .properties import MotorProperties, REV_NEO_PROPS
from .electrical_state import MotorElectricalState
from .kinematic_state import MotorKinematicState

# Primarily derived from [this great project](https://github.com/markisus/motor_sim), with some of my own tweaks

class MotorSimulation:
    properties: MotorProperties
    electrical: MotorElectricalState
    kinematic: MotorKinematicState

    def __init__(self, properties: MotorProperties):
        self.properties = properties
        self.electrical = MotorElectricalState()
        self.kinematic = MotorKinematicState()
    
    def step(self, dt: float, load_torque: float, phase_voltages: tuple[float, float, float]):
        # Clamp phase voltages because SVM would normally do this but we don't simulate it
        # This technically should never fall outside the vbus range, though
        vbus = 12
        phase_voltages = cast(tuple[float, float, float], tuple(clamp(v, -vbus, vbus) for v in phase_voltages))
        
        electrical_angle: float = self.properties.mechanical_to_electrical_angle(self.kinematic.rotor_angle)
        electrical_angular_velocity = self.properties.pole_pairs * self.kinematic.rotor_angular_velocity
        
        self.step_electrical(dt, phase_voltages, electrical_angle, electrical_angular_velocity)
        self.step_kinematic(dt, load_torque)

    def step_electrical(
        self,
        dt: float,
        phase_voltages: tuple[float, float, float],
        electrical_angle: float,
        electrical_angular_velocity: float
    ):    
        bemfs = self.properties.get_phase_backemfs(electrical_angle, electrical_angular_velocity)
        self.electrical.bemf_torques = bemfs.bemf_torques
        self.electrical.bemf_voltages = bemfs.phase_bemf

        # Calculate current derivative
        
        # Since the sum of phase voltages/currents across the three phases must be zero,
        # we subtract the average to use relative phase-neutral voltages
        # average_phase_voltage = sum(phase_voltages) / 3
        # average_bemf = sum(self.electrical.phase_bemfs) / 3
        neutral_voltage = (sum(phase_voltages) - sum(self.electrical.bemf_voltages)) / 3
        di_dt: list[float] = [0, 0, 0]
        for i in range(3):
            phase_to_neutral_voltage = phase_voltages[i] - neutral_voltage
            back_emf_voltage = self.electrical.bemf_voltages[i]
            resistive_drop = self.electrical.phase_currents[i] * self.properties.phase_resistance
            effective_voltage = phase_to_neutral_voltage - back_emf_voltage - resistive_drop
            di_dt[i] = effective_voltage / self.properties.phase_inductance
        
        # Simple Euler integration for current
        self.electrical.phase_currents = cast(
            tuple[float, float, float],
            tuple(self.electrical.phase_currents[i] + di_dt[i] * dt for i in range(3))
        )
    
    def step_kinematic(
        self,
        dt: float,
        load_torque: float
    ):  
        # Calculate applied torque
        cogging_torque: float = self.properties.get_cogging_torque_at_rotor_angle(self.kinematic.rotor_angle)
        friction_torque: float = self.properties.get_friction_torque(self.kinematic.rotor_angular_velocity)
        electromagnetic_torque: float = sum(
            current * bemf for current, bemf in zip(self.electrical.phase_currents, self.electrical.bemf_torques)
        )
        self.kinematic.torque = electromagnetic_torque + cogging_torque + friction_torque + load_torque
        
        # The equivalent of F=m*a for rotational tynamics is tau = I*a.
        # Radians are unitless, so this matches 1/s^2
        self.kinematic.rotor_angular_acceleration = self.kinematic.torque / self.properties.rotor_inertia
        # Simple Euler integration for velocity and position
        self.kinematic.rotor_angular_velocity += self.kinematic.rotor_angular_acceleration * dt
        self.kinematic.rotor_angle += self.kinematic.rotor_angular_velocity * dt
        # Wrap angle to [0, 2pi)
        self.kinematic.rotor_angle = self.kinematic.rotor_angle % (2 * math.pi)
        
    def get_encoder_position(self):
        return self.kinematic.rotor_angle

    def get_simulated_phase_currents(self):
        """Returns the simulated phase currents as a tuple (phase_a, phase_b, phase_c)."""
        return self.electrical.phase_currents


# Simulates the IO for the actual motor controller using a mocked interface and simulated motor.
class SimIOInterface:
    motor: MotorSimulation
    debug_led_state: tuple[bool, bool, bool] = (False, False, False)
    last_phase_voltages: tuple[float, float, float] = (0, 0, 0)
    
    def __init__(self):
        self.motor = MotorSimulation(REV_NEO_PROPS)
    
    def update(self, dt: float, phase_voltages: tuple[float, float, float]):
        """Update the motor simulation with the given phase inputs."""
        load_torque = 0 # Nm
        self.last_phase_voltages = phase_voltages
        self.motor.step(dt, load_torque, phase_voltages)
    
    def reset(self):
        """Reset the motor simulation to its initial state."""
        self.motor = MotorSimulation(REV_NEO_PROPS)
        self.debug_led_state = (False, False, False)
        self.last_phase_voltages = (0, 0, 0)
    
    def get_encoder_position(self) -> float:
        """Get the current encoder position of the motor in radians."""
        return self.motor.get_encoder_position()
    
    def set_debug_leds(self, led1: bool, led2: bool, led3: bool):
        # In a real implementation, this would control hardware LEDs.
        self.debug_led_state = (led1, led2, led3)
    
    def get_phase_currents(self) -> tuple[float, float, float]:
        return self.motor.get_simulated_phase_currents()