import math
import math

class MotorSimulation:
    position: float # Position in radians
    velocity: float # Velocity in rad/s
    current: float # Current in amperes
    
    current_limit: float # Current limit in amperes
    
    # Inertia in kg*m^2
    inertia: float
    # Friction coefficients
    viscous: float # Nm*s/rad
    coulomb: float # Nm
    R: float  # Resistance, ohms
    L: float  # Inductance, henries
    Kt: float  # Torque constant, Nm/A
    Ke: float  # Back-EMF constant, V/(rad/s)
    
    def __init__(self):
        self.position = 0.0
        self.velocity = 0.0
        self.current = 0.0
        self.current_limit = 10.0
        
        # I pulled these out of nowhere, who knows if they're accurate
        self.inertia = 1e-4
        self.viscous = 1e-3
        self.coulomb = 0.01
        self.R = 0.5
        self.L = 100e-6
        self.Kt = 0.02
        self.Ke = 0.02
    
    def update(self, dt: float, phase_v: float):
        # We just assume balanced 3-phase using the total phase voltage.
        # This is not accurate, but whatever for now.
        
        # Electrical dynamics: simple RL + back-EMF
        di = (phase_v - self.R * self.current - self.Ke * self.velocity) / self.L
        self.current += di * dt
        
        # Current limits prevent us from drawing more than the limit to an extent.
        # I'm not sure how to model this more accurately, but this is a start.
        if abs(self.current) > self.current_limit:
            self.current = math.copysign(self.current_limit, self.current)
        
        # Torque
        torque = self.Kt * self.current
        friction_torque = self.viscous * self.velocity + self.coulomb * math.copysign(1, self.velocity)
        accel = (torque - friction_torque) / self.inertia
        
        self.velocity += accel * dt
        self.position += self.velocity * dt
    
    def get_encoder_position(self):
        return self.position % (2 * math.pi)


# Simulates the IO for the actual motor controller using a mocked interface and simulated motor.
class SimIOInterface:
    motor: MotorSimulation
    debug_led_state: tuple[bool, bool, bool] = (False, False, False)
    
    def __init__(self):
        self.motor = MotorSimulation()
    
    def update(self, dt: float, phase_v: float):
        """Update the motor simulation with the given phase inputs."""
        self.motor.update(dt, phase_v)
    
    def get_encoder_position(self) -> float:
        """Get the current encoder position of the motor in radians."""
        return self.motor.get_encoder_position()
    
    def set_debug_leds(self, led1: bool, led2: bool, led3: bool):
        # In a real implementation, this would control hardware LEDs.
        self.debug_led_state = (led1, led2, led3)