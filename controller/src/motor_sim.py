import math
import math
class MotorSimulation:
    position: float # Position in radians
    velocity: float # Velocity in rad/s

    # Per-phase currents
    ia: float
    ib: float
    ic: float

    # Current limit in amps; not physically based or anything
    current_limit: float

    # Inertia in kg*m^2
    inertia: float
    # Friction coefficients
    viscous: float # Nm*s/rad
    coulomb: float # Nm
    R: float # Resistance, ohms (per phase)
    L: float # Inductance, henries (per phase)
    Kt: float # Torque constant, Nm/A
    Ke: float # Back-EMF constant, V/(rad/s)

    def __init__(self):
        self.position = 0.0
        self.velocity = 0.0
        self.ia = 0.0
        self.ib = 0.0
        self.ic = 0.0
        self.current_limit = 10.0

        self.inertia = 1e-4
        self.viscous = 1e-3
        self.coulomb = 0.01
        self.R = 0.5
        self.L = 100e-6
        self.Kt = 0.02
        self.Ke = 0.02

    def update(self, dt: float, phase_a: float, phase_b: float, phase_c: float):
        # Simulate per-phase RL + back-EMF
        
        # Electrical angle (assuming 1 pole pair)
        theta_e = self.position

        # Back-EMF for each phase (sinusoidal, 120 deg apart)
        emf_a = self.Ke * self.velocity * math.sin(theta_e)
        emf_b = self.Ke * self.velocity * math.sin(theta_e - 2 * math.pi / 3)
        emf_c = self.Ke * self.velocity * math.sin(theta_e + 2 * math.pi / 3)

        # di/dt for each phase
        dia = (phase_a - self.R * self.ia - emf_a) / self.L
        dib = (phase_b - self.R * self.ib - emf_b) / self.L
        dic = (phase_c - self.R * self.ic - emf_c) / self.L

        self.ia += dia * dt
        self.ib += dib * dt
        self.ic += dic * dt

        # Enforce current limit per phase... not accurate at all, but meh.
        self.ia = max(-self.current_limit, min(self.ia, self.current_limit))
        self.ib = max(-self.current_limit, min(self.ib, self.current_limit))
        self.ic = max(-self.current_limit, min(self.ic, self.current_limit))

        # Total torque is the sum of phase torques
        torque = (
            self.Kt * (
                self.ia * math.sin(theta_e) +
                self.ib * math.sin(theta_e - 2 * math.pi / 3) +
                self.ic * math.sin(theta_e + 2 * math.pi / 3)
            )
        )

        # Friction torque
        friction_torque = self.viscous * self.velocity + self.coulomb * math.copysign(1, self.velocity)
        accel = (torque - friction_torque) / self.inertia

        self.velocity += accel * dt
        self.position += self.velocity * dt

    def get_encoder_position(self):
        return self.position % (2 * math.pi)

    def get_simulated_phase_currents(self):
        """Returns the simulated phase currents as a tuple (phase_a, phase_b, phase_c)."""
        return (self.ia, self.ib, self.ic)


# Simulates the IO for the actual motor controller using a mocked interface and simulated motor.
class SimIOInterface:
    motor: MotorSimulation
    debug_led_state: tuple[bool, bool, bool] = (False, False, False)
    
    def __init__(self):
        self.motor = MotorSimulation()
    
    def update(self, dt: float, phase_a: float, phase_b: float, phase_c: float):
        """Update the motor simulation with the given phase inputs."""
        self.motor.update(dt, phase_a, phase_b, phase_c)
    
    def get_encoder_position(self) -> float:
        """Get the current encoder position of the motor in radians."""
        return self.motor.get_encoder_position()
    
    def set_debug_leds(self, led1: bool, led2: bool, led3: bool):
        # In a real implementation, this would control hardware LEDs.
        self.debug_led_state = (led1, led2, led3)