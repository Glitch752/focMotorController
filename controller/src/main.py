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
    
    kp_id: float # Proportional gain for d-axis current
    ki_id: float # Integral gain for d-axis current
    kp_iq: float # Proportional gain for q-axis current
    ki_iq: float # Integral gain for q-axis current
    id_int: float # Integral term for d-axis current
    iq_int: float # Integral term for q-axis current
    
    target_iq: float # Target q-axis current (torque command)
    
    last_output_phase_a: float
    last_output_phase_b: float
    last_output_phase_c: float
    
    def __init__(self, io: SimIOInterface):
        self.io = io
        self.angle = 0.0
        self.vel = 0.0
        
        # control gains
        self.kp_id = 1.0
        self.ki_id = 10.0
        self.kp_iq = 1.0
        self.ki_iq = 10.0
        self.id_int = 0.0
        self.iq_int = 0.0
        
        self.target_iq = 1.0
        
    def step(self, dt):
        # Measure position and estimate velocity
        pos = self.io.get_encoder_position()
        delta = (pos - self.angle + math.pi) % (2 * math.pi) - math.pi
        self.vel = delta / dt
        self.angle = pos
        
        # Clarke and Park transforms but only with one phase
        id_meas = self.io.motor.current * math.cos(self.angle)
        iq_meas = self.io.motor.current * math.sin(self.angle)
        
        # PI current controllers
        err_id = -id_meas
        err_iq = self.target_iq - iq_meas
        
        self.id_int += err_id * self.ki_id * dt
        self.iq_int += err_iq * self.ki_iq * dt
        
        u_id = self.kp_id * err_id + self.id_int
        u_iq = self.kp_iq * err_iq + self.iq_int
        
        # Inverse Park-Clarke to get phase voltage
        u_alpha =  u_id * math.cos(self.angle) - u_iq * math.sin(self.angle)
        phase_v = u_alpha # Simplified single-phase representation; TODO: expand to three phases
        
        self.last_output_phase_a = phase_v
        self.last_output_phase_b = phase_v
        self.last_output_phase_c = phase_v
        
        self.io.update(dt, phase_v)

def main():
    print("--- FOC motor controller simulation ---")
    
    io = SimIOInterface()
    ctrl = FOCController(io)
    dt = 0.001 # 1 ms timestep
    import dearpygui.dearpygui as dpg

    dpg.create_context()
    dpg.create_viewport()
    dpg.setup_dearpygui()

    max_values = 1000
    times = []
    angles = []
    phase_a_voltages = []
    phase_b_voltages = []
    phase_c_voltages = []
    
    with dpg.window(label="Motor Controller"):
        angle_plot = dpg.add_plot(label="Rotor Angle", height=400, width=1000)
        dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", parent=angle_plot)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Angle (rad)", parent=angle_plot)
        
        angle_series = dpg.add_line_series([], [], label="Angle", parent=y_axis)
        # dpg.set_axis_limits(y_axis, 0, 2 * math.pi)
        
        phase_a_series = dpg.add_line_series([], [], label="Phase A Voltage", parent=y_axis)
        phase_b_series = dpg.add_line_series([], [], label="Phase B Voltage", parent=y_axis)
        phase_c_series = dpg.add_line_series([], [], label="Phase C Voltage", parent=y_axis)
        
        vel_text = dpg.add_text(default_value="Velocity: 0.00 rad/s")

    def update_gui(delta: float):
        delta = min(delta, 100) # Cap delta to avoid too large jumps
        while delta > dt:
            delta -= dt
            
            ctrl.step(dt)
            
            t = len(times) * dt
            times.append(t)
            angles.append(io.get_encoder_position())
            
            phase_a_voltages.append(ctrl.last_output_phase_a)
            phase_b_voltages.append(ctrl.last_output_phase_b)
            phase_c_voltages.append(ctrl.last_output_phase_c)
        
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
