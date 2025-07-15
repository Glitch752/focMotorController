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
    
    target_id: float # Target d-axis current
    target_iq: float # Target q-axis current (torque command)
    
    last_phase_voltages: tuple[float, float, float]
    
    current_dq: tuple[float, float]
    output_dq: tuple[float, float]
    
    def __init__(self, io: SimIOInterface):
        self.io = io
        self.angle = 0.0
        self.vel = 0.0
        
        self.id_controller = self.IDController(kp=10, ki=0.0)
        self.iq_controller = self.IDController(kp=10, ki=0.0)
        
        self.target_id = 0
        self.target_iq = 10
        
    def step(self, dt):
        # Measure position and estimate velocity
        theta = self.io.get_encoder_position()
        
        delta = (theta - self.angle + math.pi) % (2 * math.pi) - math.pi
        self.vel = delta / dt
        self.angle = theta
        
        i_a, i_b, i_c = self.io.motor.get_simulated_phase_currents()
        clarke = transforms.clarke_transform(i_a, i_b, i_c)
        (i_d, i_q) = transforms.park_transform(clarke, theta)
        self.current_dq = (i_d, i_q)
        
        u_id = self.id_controller.compute(self.target_id - i_d, dt)
        u_iq = self.iq_controller.compute(self.target_iq - i_q, dt)
        self.output_dq = (u_id, u_iq)
        
        dq_voltages = transforms.ParkOutput(u_id, u_iq).clamp_to_vbus(self.io.motor.properties.vbus)
        park_voltages = transforms.inverse_park_transform(dq_voltages, theta)
        phase_voltages = transforms.inverse_clarke_transform(park_voltages)
        
        self.last_phase_voltages = phase_voltages

        self.io.update(dt, phase_voltages)

def main():
    print("--- FOC motor controller simulation ---")
    
    io = SimIOInterface()
    ctrl = FOCController(io)
    dt = 0.00001 # 0.1 ms timestep
    import dearpygui.dearpygui as dpg

    dpg.create_context()
    dpg.create_viewport()
    dpg.setup_dearpygui()

    SHOW_LATEST_GRAPH = True
    
    GRAPH_ANGLE = False
    GRAPH_PHASE_VOLTAGES = True
    GRAPH_CURRENT_DQ = False
    GRAPH_OUTPUT_DQ = False
    
    paused = False

    max_values = 500
    sample_separation = 100
    times = []
    
    angles = []
    
    phase_u_voltages = []
    phase_v_voltages = []
    phase_w_voltages = []
    
    curr_d_currents = []
    curr_q_currents = []
    
    out_d_voltages = []
    out_q_voltages = []
    
    with dpg.window(label="Motor Controller"):
        angle_plot = dpg.add_plot(label="Rotor Angle", height=400, width=1000)
        x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", parent=angle_plot)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Angle (rad)", parent=angle_plot)
        
        if SHOW_LATEST_GRAPH:
            dpg.set_axis_limits(x_axis, 0, max_values * dt * sample_separation)
        
        if GRAPH_ANGLE:
            angle_series = dpg.add_line_series([], [], label="Angle", parent=y_axis)
            # dpg.set_axis_limits(y_axis, 0, 2 * math.pi)
        if GRAPH_PHASE_VOLTAGES:
            phase_u_series = dpg.add_line_series([], [], label="Phase A Voltage", parent=y_axis)
            phase_v_series = dpg.add_line_series([], [], label="Phase B Voltage", parent=y_axis)
            phase_w_series = dpg.add_line_series([], [], label="Phase C Voltage", parent=y_axis)
        if GRAPH_CURRENT_DQ:
            curr_d_series = dpg.add_line_series([], [], label="D-axis Current", parent=y_axis)
            curr_q_series = dpg.add_line_series([], [], label="Q-axis Current", parent=y_axis)
        if GRAPH_OUTPUT_DQ:
            d_series = dpg.add_line_series([], [], label="D-axis Voltage Output", parent=y_axis)
            q_series = dpg.add_line_series([], [], label="Q-axis Voltage Output", parent=y_axis)
        
        info_text = dpg.add_text(default_value="")
        
        # Add pause/play button
        def toggle_pause():
            nonlocal paused
            paused = not paused
            dpg.set_value(pause_button, "Resume" if paused else "Pause")
        pause_button = dpg.add_button(label="Pause", callback=toggle_pause)

    elapsed = 0
    def update_gui(delta: float):
        nonlocal elapsed
        
        updates_per_frame = 1000
        for i in range(updates_per_frame):
            ctrl.step(dt)
            
            elapsed += dt
            
            if i % sample_separation == 0:
                if SHOW_LATEST_GRAPH:
                    if len(times) < max_values:
                        times.append(elapsed)
                else:
                    times.append(elapsed)
            
                if GRAPH_ANGLE:
                    angles.append(io.get_encoder_position())
                if GRAPH_PHASE_VOLTAGES:
                    phase_u_voltages.append(ctrl.last_phase_voltages[0])
                    phase_v_voltages.append(ctrl.last_phase_voltages[1])
                    phase_w_voltages.append(ctrl.last_phase_voltages[2])
                if GRAPH_CURRENT_DQ:
                    curr_d_currents.append(ctrl.current_dq[0])
                    curr_q_currents.append(ctrl.current_dq[1])
                if GRAPH_OUTPUT_DQ:
                    out_d_voltages.append(ctrl.output_dq[0])
                    out_q_voltages.append(ctrl.output_dq[1])
                
                if len(times) > max_values:
                    times.pop(0)
                if GRAPH_ANGLE and len(angles) > max_values:
                    angles.pop(0)
                if GRAPH_PHASE_VOLTAGES and len(phase_u_voltages) > max_values:
                    phase_u_voltages.pop(0)
                    phase_v_voltages.pop(0)
                    phase_w_voltages.pop(0)
                if GRAPH_CURRENT_DQ and len(curr_d_currents) > max_values:
                    curr_d_currents.pop(0)
                    curr_q_currents.pop(0)
                if GRAPH_OUTPUT_DQ and len(out_d_voltages) > max_values:
                    out_d_voltages.pop(0)
                    out_q_voltages.pop(0)
        
        if GRAPH_ANGLE:
            dpg.set_value(angle_series, [times, angles])
        if GRAPH_PHASE_VOLTAGES:
            dpg.set_value(phase_u_series, [times, phase_u_voltages])
            dpg.set_value(phase_v_series, [times, phase_v_voltages])
            dpg.set_value(phase_w_series, [times, phase_w_voltages])
        if GRAPH_CURRENT_DQ:
            dpg.set_value(curr_d_series, [times, curr_d_currents])
            dpg.set_value(curr_q_series, [times, curr_q_currents])
        if GRAPH_OUTPUT_DQ:
            dpg.set_value(d_series, [times, out_d_voltages])
            dpg.set_value(q_series, [times, out_q_voltages])
        
        dpg.set_value(info_text, f"Velocity: {ctrl.vel:.2f} rad/s\n\
Angle: {ctrl.angle:.4f}\n\
Current update rate: {updates_per_frame / delta:.2f} Hz")
    
    dpg.show_viewport()

    last_time = time.time()
    while dpg.is_dearpygui_running():
        delta = time.time() - last_time
        last_time += delta
        
        if not paused:
            update_gui(delta)
        
        dpg.render_dearpygui_frame()

    dpg.destroy_context()

if __name__ == "__main__":
    main()
