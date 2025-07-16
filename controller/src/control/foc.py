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
    dq_integral_terms: tuple[float, float]

    def __init__(self, io: SimIOInterface):
        self.io = io
        self.angle = 0.0
        self.vel = 0.0

        (p, i) = self.make_motor_pi_params(10000)
        self.id_controller = IDController(kp=p, ki=i)
        self.iq_controller = IDController(kp=p, ki=i)

        self.target_id = 0
        self.target_iq = -1
    
    def make_motor_pi_params(self, bandwidth: float):
        p = self.io.motor.properties.phase_inductance * bandwidth
        i = self.io.motor.properties.phase_resistance * bandwidth
        return (p, i)
    
    def reset(self):
        self.angle = 0.0
        self.vel = 0.0
        self.id_controller.reset()
        self.iq_controller.reset()
        self.target_id = 0
        self.target_iq = -1

    def get_phase_voltages(self, dt: float) -> tuple[float, float, float]:
        theta = self.io.get_encoder_position()
        q_axis_angle = self.io.motor.properties.mechanical_to_electrical_angle(theta) + math.pi / 4

        delta = (q_axis_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
        self.vel = delta / dt
        self.angle = q_axis_angle

        i_a, i_b, i_c = self.io.get_phase_currents()
        clarke = transforms.clarke_transform(i_a, i_b, i_c)
        (i_d, i_q) = transforms.park_transform(clarke, q_axis_angle)
        self.current_dq = (i_d, i_q)

        u_id = self.id_controller.compute(self.target_id - i_d, dt)
        u_iq = self.iq_controller.compute(self.target_iq - i_q, dt)
        self.output_dq = (u_id, u_iq)
        self.dq_integral_terms = (self.id_controller.int, self.iq_controller.int)

        dq_voltages = transforms.ParkOutput(u_id, u_iq).clamp_to_vbus(self.io.motor.properties.vbus)
        park_voltages = transforms.inverse_park_transform(dq_voltages, q_axis_angle)
        phase_voltages = transforms.inverse_clarke_transform(park_voltages)

        return phase_voltages