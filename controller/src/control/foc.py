from ..control import MotorController, transforms
from ..control.id import IDController
from ..motor_sim import SimIOInterface
import math

class FOCController(MotorController):
    io: SimIOInterface
    angle: float # Radians, from encoder
    vel: float # Rad/s, estimated

    # D-axis and Q-axis current controllers
    id_controller: IDController
    iq_controller: IDController

    target_id: float # Target d-axis voltage
    target_iq: float # Target q-axis voltage (torque command)

    current_dq: tuple[float, float]
    output_dq: tuple[float, float]

    def __init__(self, io: SimIOInterface):
        self.io = io
        self.angle = 0.0
        self.vel = 0.0

        self.id_controller = IDController(kp=10, ki=0.0)
        self.iq_controller = IDController(kp=10, ki=0.0)

        self.target_id = 0
        self.target_iq = 10
    
    def reset(self):
        self.angle = 0.0
        self.vel = 0.0
        self.id_controller.reset()
        self.iq_controller.reset()
        self.target_id = 0
        self.target_iq = 10

    def get_phase_voltages(self, dt: float) -> tuple[float, float, float]:
        # Measure position and estimate velocity
        theta = self.io.get_encoder_position() - math.pi / 4

        delta = (theta - self.angle + math.pi) % (2 * math.pi) - math.pi
        self.vel = delta / dt
        self.angle = theta

        i_a, i_b, i_c = self.io.get_phase_currents()
        clarke = transforms.clarke_transform(i_a, i_b, i_c)
        (i_d, i_q) = transforms.park_transform(clarke, theta)
        self.current_dq = (i_d, i_q)

        u_id = self.id_controller.compute(self.target_id - i_d, dt)
        u_iq = self.iq_controller.compute(self.target_iq - i_q, dt)
        self.output_dq = (u_id, u_iq)

        dq_voltages = transforms.ParkOutput(u_id, u_iq).clamp_to_vbus(self.io.motor.properties.vbus)
        park_voltages = transforms.inverse_park_transform(dq_voltages, theta)
        phase_voltages = transforms.inverse_clarke_transform(park_voltages)

        return phase_voltages