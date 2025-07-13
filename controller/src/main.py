import math
import time

from .motor_sim import SimIOInterface

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
    
    last_output_phase_a: float
    last_output_phase_b: float
    last_output_phase_c: float
    
    def __init__(self, io: SimIOInterface):
        self.io = io
        self.angle = 0.0
        self.vel = 0.0
        
        self.id_controller = self.IDController(kp=0.1, ki=0.01)
        self.iq_controller = self.IDController(kp=0.1, ki=0.01)
        
        self.target_iq = 1.0
        
    def step(self, dt):
        # Measure position and estimate velocity
        pos = self.io.get_encoder_position()
        delta = (pos - self.angle + math.pi) % (2 * math.pi) - math.pi
        self.vel = delta / dt
        self.angle = pos
        
        # Park-Clarke transformation
        # Okay, this is DEFINITELY not right but I'll eventually figure it out (maybe)
        i_a, i_b, i_c = self.io.motor.get_simulated_phase_currents()
        i_alpha = (i_a - i_b) / math.sqrt(3)
        i_beta = (i_a + 2 * i_b) / math.sqrt(3)
        i_d = i_alpha * math.cos(self.angle) + i_beta * math.sin(self.angle)
        i_q = -i_alpha * math.sin(self.angle) + i_beta * math.cos(self.angle)
        
        # individual axis currents
        i_d_target = 0.0  # d-axis current target (usually 0 for BLDC)
        i_q_target = self.target_iq  # q-axis current target (torque command)
        
        u_id = self.id_controller.compute(i_d_target - i_d, dt)
        u_iq = self.iq_controller.compute(i_q_target - i_q, dt)
        
        # Inverse Park-Clarke to get phase voltage
        phase_a = 2 / 3 * (u_id * math.cos(self.angle) + u_iq * math.sin(self.angle))
        phase_b = 2 / 3 * (-u_id * 0.5 + u_iq * math.sqrt(3) / 2)
        phase_c = 2 / 3 * (-u_id * 0.5 - u_iq * math.sqrt(3) / 2)

        self.last_output_phase_a = phase_a
        self.last_output_phase_b = phase_b
        self.last_output_phase_c = phase_c

        self.io.update(dt, phase_a, phase_b, phase_c)

def main():
    print("--- FOC motor controller simulation ---")
    
    io = SimIOInterface()
    ctrl = FOCController(io)
    dt = 0.001 # 1 ms timestep
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
        
        if SHOW_LATEST_GRAPH:
            dpg.set_axis_limits(x_axis, 0, max_values * dt)
        
        phase_a_series = dpg.add_line_series([], [], label="Phase A Voltage", parent=y_axis)
        phase_b_series = dpg.add_line_series([], [], label="Phase B Voltage", parent=y_axis)
        phase_c_series = dpg.add_line_series([], [], label="Phase C Voltage", parent=y_axis)
        
        vel_text = dpg.add_text(default_value="Velocity: 0.00 rad/s")

    elapsed = 0
    def update_gui(delta: float):
        nonlocal elapsed
        
        delta = min(delta, 100) # Cap delta to avoid too large jumps
        while delta > dt:
            delta -= dt
            
            ctrl.step(dt)
            
            elapsed += dt
            
            if SHOW_LATEST_GRAPH:
                if len(times) < max_values:
                    times.append(len(times) * dt)
            else:
                times.append(elapsed)
            
            angles.append(io.get_encoder_position())
            phase_a_voltages.append(ctrl.last_output_phase_a)
            phase_b_voltages.append(ctrl.last_output_phase_b)
            phase_c_voltages.append(ctrl.last_output_phase_c)
            
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
        
        update_gui(delta)
        
        dpg.render_dearpygui_frame()

    dpg.destroy_context()

if __name__ == "__main__":
    main()
