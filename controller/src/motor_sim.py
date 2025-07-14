import math
import math
class MotorSimulation:
    position: float # Position in radians
    velocity: float # Velocity in rad/s

    # Per-phase currents
    iu: float
    iv: float
    iw: float

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
        self.iu = 0.0
        self.iv = 0.0
        self.iw = 0.0

        self.inertia = 1e-4
        self.viscous = 1e-3
        self.coulomb = 0.01
        self.R = 0.5
        self.L = 100e-6
        self.Kt = 0.02
        self.Ke = 0.02

    def update(self, dt: float, phase_u: float, phase_v: float, phase_w: float):
        vbus = 12.0  # TODO: Simulate voltage drop, maybe?
        
        vu = (phase_u - 0.5) * vbus
        vv = (phase_v - 0.5) * vbus
        vw = (phase_w - 0.5) * vbus

        # Calculate back-EMF for each phase
        theta = self.position
        emf_u = self.Ke * self.velocity * math.sin(theta)
        emf_v = self.Ke * self.velocity * math.sin(theta - 2 * math.pi / 3)
        emf_w = self.Ke * self.velocity * math.sin(theta + 2 * math.pi / 3)

        # Update phase currents using simple RL circuit model
        diu = (vu - emf_u - self.R * self.iu) / self.L
        div = (vv - emf_v - self.R * self.iv) / self.L
        diw = (vw - emf_w - self.R * self.iw) / self.L
        
        self.iu += diu * dt
        self.iv += div * dt
        self.iw += diw * dt

        torque = self.Kt * (
            self.iu * math.sin(theta) +
            self.iv * math.sin(theta - 2 * math.pi / 3) +
            self.iw * math.sin(theta + 2 * math.pi / 3)
        )

        # Friction torques
        torque_friction = self.viscous * self.velocity + math.copysign(self.coulomb, self.velocity)
        net_torque = torque - torque_friction

        accel = net_torque / self.inertia
        self.velocity += accel * dt
        self.position += self.velocity * dt

    def get_encoder_position(self):
        return self.position % (2 * math.pi)

    def get_simulated_phase_currents(self):
        """Returns the simulated phase currents as a tuple (phase_a, phase_b, phase_c)."""
        return (self.iu, self.iv, self.iw)


# Simulates the IO for the actual motor controller using a mocked interface and simulated motor.
class SimIOInterface:
    motor: MotorSimulation
    debug_led_state: tuple[bool, bool, bool] = (False, False, False)
    
    def __init__(self):
        self.motor = MotorSimulation()
    
    def update(self, dt: float, phase_u: float, phase_v: float, phase_w: float):
        """Update the motor simulation with the given phase inputs."""
        self.motor.update(dt, phase_u, phase_v, phase_w)
    
    def get_encoder_position(self) -> float:
        """Get the current encoder position of the motor in radians."""
        return self.motor.get_encoder_position()
    
    def set_debug_leds(self, led1: bool, led2: bool, led3: bool):
        # In a real implementation, this would control hardware LEDs.
        self.debug_led_state = (led1, led2, led3)