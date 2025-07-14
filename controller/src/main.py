import math
import time

from .motor_sim import SimIOInterface
from . import transforms

class FOCController:
    """
    I have no clue if this math is correct; for now, I'm heavily referencing [Arduino-FOC](https://github.com/simplefoc/Arduino-FOC) and [this project](https://github.com/markisus/motor_sim).
    """
    
    io: SimIOInterface
    angle: float # Radians, from encoder
    vel: float # Rad/s, estimated
    
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

    # D-axis and Q-axis current controllers
    id_controller: "FOCController.IDController"
    iq_controller: "FOCController.IDController"
    
    target_iq: float # Target q-axis current (torque command)
    
    last_output_u: float
    last_output_v: float
    last_output_w: float
    
    def __init__(self, io: SimIOInterface):
        self.io = io
        self.angle = 0.0
        self.vel = 0.0
        
        self.id_controller = self.IDController(kp=1e-5, ki=0.0)
        self.iq_controller = self.IDController(kp=1e-5, ki=0.0)
        
        self.target_iq = 1
        
    def step(self, dt):
        # Measure position and estimate velocity
        theta = self.io.get_encoder_position()
        
        delta = (theta - self.angle + math.pi) % (2 * math.pi) - math.pi
        self.vel = delta / dt
        self.angle = theta
        
        i_a, i_b, i_c = self.io.motor.get_simulated_phase_currents()
        clarke = transforms.clarke_transform(i_a, i_b, i_c)
        (i_d, i_q) = transforms.park_transform(clarke, theta)
        
        # d-axis current target (0 for FOC control)
        i_d_target = 0.0
        # q-axis current target (our torque command)
        i_q_target = self.target_iq
        
        u_id = self.id_controller.compute(i_d - i_d_target, dt)
        u_iq = self.iq_controller.compute(i_q - i_q_target, dt)
        
        park = transforms.inverse_park_transform(transforms.ParkOutput(u_id, u_iq), theta)
        (phase_u, phase_v, phase_w) = transforms.inverse_clarke_transform(park)
        
        phase_u = min(1, max(-1, phase_u))
        phase_v = min(1, max(-1, phase_v))
        phase_w = min(1, max(-1, phase_w))
        
        self.last_output_u = phase_u
        self.last_output_v = phase_v
        self.last_output_w = phase_w

        self.io.update(dt, phase_u, phase_v, phase_w)

def main():
    print("--- FOC motor controller simulation ---")
    
    io = SimIOInterface()
    ctrl = FOCController(io)
    dt = 0.0001 # 1 ms timestep
    import dearpygui.dearpygui as dpg

    dpg.create_context()
    dpg.create_viewport()
    dpg.setup_dearpygui()

    SHOW_LATEST_GRAPH = True

    max_values = 500
    times = []
    angles = []
    phase_a_voltages = []
    phase_b_voltages = []
    phase_c_voltages = []
    
    with dpg.window(label="Motor Controller"):
        angle_plot = dpg.add_plot(label="Rotor Angle", height=400, width=1000)
        x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", parent=angle_plot)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Angle (rad)", parent=angle_plot)
        
        angle_series = dpg.add_line_series([], [], label="Angle", parent=y_axis)
        # dpg.set_axis_limits(y_axis, 0, 2 * math.pi)
        
        # if SHOW_LATEST_GRAPH:
        #     dpg.set_axis_limits(x_axis, 0, max_values * dt)
        
        phase_a_series = dpg.add_line_series([], [], label="Phase A Voltage", parent=y_axis)
        phase_b_series = dpg.add_line_series([], [], label="Phase B Voltage", parent=y_axis)
        phase_c_series = dpg.add_line_series([], [], label="Phase C Voltage", parent=y_axis)
        
        vel_text = dpg.add_text(default_value="Velocity: 0.00 rad/s")

    elapsed = 0
    def update_gui():
        nonlocal elapsed
        
        for i in range(100):
            ctrl.step(dt)
            
            elapsed += dt
            
            if i % 10 == 0:
                if SHOW_LATEST_GRAPH:
                    if len(times) < max_values:
                        times.append(len(times) * dt)
                else:
                    times.append(elapsed)
            
                angles.append(io.get_encoder_position())
                phase_a_voltages.append(ctrl.last_output_u)
                phase_b_voltages.append(ctrl.last_output_v)
                phase_c_voltages.append(ctrl.last_output_w)
                
                if len(times) > max_values:
                    times.pop(0)
                if len(angles) > max_values:
                    angles.pop(0)
                    phase_a_voltages.pop(0)
                    phase_b_voltages.pop(0)
                    phase_c_voltages.pop(0)
        
        dpg.set_value(angle_series, [times, angles])
        dpg.set_value(phase_a_series, [times, phase_a_voltages])
        dpg.set_value(phase_b_series, [times, phase_b_voltages])
        dpg.set_value(phase_c_series, [times, phase_c_voltages])
        
        dpg.set_value(vel_text, f"Velocity: {ctrl.vel:.2f} rad/s")
    
    dpg.show_viewport()

    last_time = time.time()
    while dpg.is_dearpygui_running():
        delta = time.time() - last_time
        last_time += delta
        
        update_gui()
        
        dpg.render_dearpygui_frame()

    dpg.destroy_context()

if __name__ == "__main__":
    main()
