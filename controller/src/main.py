import math
import time

from .control.six_step import SixStepController
from .control.foc import FOCController
from .control import MotorController

from .motor_sim import SimIOInterface

TIMESTEP = 0.0001 # 0.1 ms timestep
# Dependent on 60fps, but whatever
REALTIME_UPDATES_PER_FRAME = int(1 / TIMESTEP / 60)

def main():
    from .plot import TimeSeriesPlot
    import dearpygui.dearpygui as dpg

    print("--- FOC motor controller simulation ---")
    
    io = SimIOInterface()
    ctrl: MotorController = FOCController(io)

    dpg.create_context()
        
    with dpg.font_registry():
        default_font = dpg.add_font("RobotoMono-Regular.ttf", 24)


    dpg.create_viewport(min_width=2000)
    dpg.setup_dearpygui()

    paused = True
    updates_per_frame = REALTIME_UPDATES_PER_FRAME
    history_length = 0.05
    sample_separation = 2
    
    plots: list[TimeSeriesPlot] = []
    
    with dpg.window(label="Simulation", width=600, height=1000):
        info_text = dpg.add_text(default_value="")
        
        with dpg.group(horizontal=True):
            # Pause/play button
            def toggle_pause():
                nonlocal paused
                paused = not paused
                dpg.set_item_label(pause_button, "Resume" if paused else "Pause")
            pause_button = dpg.add_button(label="Resume" if paused else "Pause", callback=toggle_pause)
            
            # Restart button
            def restart_simulation():
                io.reset()
                ctrl.reset()
            dpg.add_button(label="Restart", callback=restart_simulation)
            
        dpg.add_separator()
        
        # Controller type
        def change_controller(_id, controller):
            nonlocal ctrl
            if controller == "FOC":
                ctrl = FOCController(io)
            elif controller == "Six-step":
                ctrl = SixStepController(io)
        dpg.add_text("Controller type")
        dpg.add_radio_button(["FOC", "Six-step"], callback=change_controller, horizontal=True)
        
        dpg.add_separator()
        
        # Target updates per frame
        def change_updates_per_frame(sender, app_data):
            nonlocal updates_per_frame
            updates_per_frame = app_data
        dpg.add_slider_int(
            label="Updates per frame",
            default_value=updates_per_frame,
            min_value=1,
            max_value=REALTIME_UPDATES_PER_FRAME,
            callback=change_updates_per_frame
        )
        
        # Sample separation
        def change_sample_separation(sender, app_data):
            nonlocal sample_separation
            sample_separation = app_data
        dpg.add_slider_int(
            label="Sample separation",
            default_value=sample_separation,
            min_value=1,
            max_value=100,
            callback=change_sample_separation
        )
        
        # History length
        def change_history_length(sender, app_data):
            nonlocal history_length
            history_length = app_data
            
            for plot in plots:
                plot.history_length = history_length
        
        dpg.add_slider_float(
            label="History length (s)",
            default_value=history_length,
            min_value=0.01,
            max_value=1.0,
            callback=change_history_length
        )

    with dpg.window(label="Graphs", pos=(600, 0), height=1500):
        dpg.bind_font(default_font)

        with dpg.group(horizontal=False):
            def p(plot: TimeSeriesPlot) -> TimeSeriesPlot:
                plots.append(plot)
                return plot
            
            # Create plots for different data types
            angle_plot = p(TimeSeriesPlot("Rotor Angle", "Angle (rad)", history_length, default_visible=False))
            angle_plot.set_y_range(0, 2*math.pi)
            velocity_plot = p(TimeSeriesPlot("Rotor Velocity", "Velocity (RPM)", history_length, default_visible=True))
            voltage_plot = p(TimeSeriesPlot("Phase Voltages", "Voltage (V)", history_length, default_visible=True))
            phase_current_plot = p(TimeSeriesPlot("Phase Currents", "Current (A)", history_length, default_visible=False))
            dq_current_plot = p(TimeSeriesPlot("DQ Currents", "Current (A)",  history_length, default_visible=False))
            dq_output_plot = p(TimeSeriesPlot("DQ Voltage Output", "Voltage (V)", history_length, default_visible=False))
            dq_integral_plot = p(TimeSeriesPlot("DQ Integral Terms", "Integral (V)", history_length, default_visible=False))
            torque_plot = p(TimeSeriesPlot("Torque", "Torque (Nm)", history_length, default_visible=False))

    elapsed = 0
    updates_since_sample = 0
    def update_gui(delta: float):
        nonlocal elapsed, updates_since_sample
        
        for i in range(updates_per_frame):
            phase_voltages = ctrl.get_phase_voltages(TIMESTEP)
            io.update(TIMESTEP, phase_voltages)
        
            elapsed += TIMESTEP
            
            updates_since_sample += 1
            if updates_since_sample >= sample_separation:
                updates_since_sample = 0
                # Add data to plots
                angle_plot.add_data_point(elapsed, {"Angle": io.get_encoder_position()})
                
                velocity_plot.add_data_point(elapsed, {
                    "Velocity": io.motor.kinematic.rotor_angular_velocity * 60 / (2 * math.pi)
                })
                
                voltage_plot.add_data_point(elapsed, {
                    "Phase U": io.last_phase_voltages[0],
                    "Phase V": io.last_phase_voltages[1],
                    "Phase W": io.last_phase_voltages[2]
                })
                
                phase_currents = io.get_phase_currents()
                phase_current_plot.add_data_point(elapsed, {
                    "Phase U": phase_currents[0],
                    "Phase V": phase_currents[1],
                    "Phase W": phase_currents[2]
                })
                
                if isinstance(ctrl, FOCController):
                    dq_current_plot.add_data_point(elapsed, {
                        "D-axis": ctrl.current_dq[0],
                        "Q-axis": ctrl.current_dq[1]
                    })
                    
                    dq_output_plot.add_data_point(elapsed, {
                        "D-axis": ctrl.output_dq[0],
                        "Q-axis": ctrl.output_dq[1]
                    })
                    
                    dq_integral_plot.add_data_point(elapsed, {
                        "D-axis": ctrl.dq_integral_terms[0],
                        "Q-axis": ctrl.dq_integral_terms[1]
                    })
                
                torque_plot.add_data_point(elapsed, {
                    "Total torque": io.motor.kinematic.torque,
                    "Electromagnetic torque": io.motor.kinematic.electromagnetic_torque,
                    "bEMF U torque": io.motor.electrical.bemf_torques[0] * phase_currents[0],
                    "bEMF V torque": io.motor.electrical.bemf_torques[1] * phase_currents[1],
                    "bEMF W torque": io.motor.electrical.bemf_torques[2] * phase_currents[2]
                })
        
        # Update all plots
        for plot in plots:
            plot.update_plot()
        
        update_rate = updates_per_frame / delta
        velocity = io.motor.kinematic.rotor_angular_velocity
        velocity_rpm = velocity * 60 / (2 * math.pi)
        
        dpg.set_value(info_text, f"Velocity: {velocity:.2f} rad/s\n\
Velocity: {velocity_rpm:.2f} RPM\n\
Angle: {io.motor.kinematic.rotor_angle:.4f}\n\
\n\
Current update rate: {update_rate:.2f} Hz\n\
Realtime ratio: {(update_rate / (1 / TIMESTEP)) * 100:.1f}%\n\
Total output torque: {io.motor.kinematic.torque:.2f} Nm")
    
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
