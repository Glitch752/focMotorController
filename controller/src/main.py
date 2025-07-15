import math
import time

from .control.six_step import SixStepController
from .control.foc import FOCController
from .control import MotorController

from .motor_sim import SimIOInterface

TIMESTEP = 0.00001 # 0.1 ms timestep
SAMPLE_SEPARATION = 500
UPDATES_PER_FRAME = 1000

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

    SHOW_ANGLE_PLOT = True
    SHOW_PHASE_VOLTAGES_PLOT = True
    SHOW_PHASE_CURRENTS_PLOT = False
    SHOW_CURRENT_DQ_PLOT = False
    SHOW_OUTPUT_DQ_PLOT = False
    SHOW_TORQUES = True

    paused = True
    max_values = 500
    
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
            
        # Controller type
        def change_controller(_id, controller):
            nonlocal ctrl
            if controller == "FOC":
                ctrl = FOCController(io)
            elif controller == "Six-step":
                ctrl = SixStepController(io)
        dpg.add_text("Controller type")
        dpg.add_radio_button(["FOC", "Six-step"], callback=change_controller, horizontal=True)

    with dpg.window(label="Graphs", pos=(600, 0), height=1500):
        dpg.bind_font(default_font)

        with dpg.group(horizontal=False):
            # Create plots for different data types
            angle_plot = TimeSeriesPlot("Rotor Angle", "Angle (rad)", max_values, visible=SHOW_ANGLE_PLOT)
            if SHOW_ANGLE_PLOT:
                angle_plot.set_y_range(0, 2*math.pi)
                angle_plot.add_series("Angle")
            
            voltage_plot = TimeSeriesPlot("Phase Voltages", "Voltage (V)", max_values, visible=SHOW_PHASE_VOLTAGES_PLOT)
            if SHOW_PHASE_VOLTAGES_PLOT:
                voltage_plot.add_series("Phase U")
                voltage_plot.add_series("Phase V")
                voltage_plot.add_series("Phase W")
            
            phase_current_plot = TimeSeriesPlot("Phase Currents", "Current (A)", max_values, visible=SHOW_PHASE_CURRENTS_PLOT)
            if SHOW_PHASE_CURRENTS_PLOT:
                phase_current_plot.add_series("Phase U")
                phase_current_plot.add_series("Phase V")
                phase_current_plot.add_series("Phase W")
            
            current_plot = TimeSeriesPlot("DQ Currents", "Current (A)",  max_values, visible=SHOW_CURRENT_DQ_PLOT)
            if SHOW_CURRENT_DQ_PLOT:
                current_plot.add_series("D-axis")
                current_plot.add_series("Q-axis")
            
            output_plot = TimeSeriesPlot("DQ Voltage Output", "Voltage (V)",  max_values, visible=SHOW_OUTPUT_DQ_PLOT)
            if SHOW_OUTPUT_DQ_PLOT:
                output_plot.add_series("D-axis")
                output_plot.add_series("Q-axis")
                
            torque_plot = TimeSeriesPlot("Torque", "Torque (Nm)", max_values, visible=SHOW_TORQUES)
            if SHOW_TORQUES:
                torque_plot.add_series("Total torque")
                torque_plot.add_series("bEMF U torque")
                torque_plot.add_series("bEMF V torque")
                torque_plot.add_series("bEMF W torque")

    elapsed = 0
    def update_gui(delta: float):
        nonlocal elapsed
        
        for i in range(UPDATES_PER_FRAME):
            phase_voltages = ctrl.get_phase_voltages(TIMESTEP)
            io.update(TIMESTEP, phase_voltages)
        
            elapsed += TIMESTEP
            
            if i % SAMPLE_SEPARATION == 0:
                # Add data to plots
                angle_plot.add_data_point(elapsed, {"Angle": io.get_encoder_position()})
                
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
                    current_plot.add_data_point(elapsed, {
                        "D-axis": ctrl.current_dq[0],
                        "Q-axis": ctrl.current_dq[1]
                    })
                    
                    output_plot.add_data_point(elapsed, {
                        "D-axis": ctrl.output_dq[0],
                        "Q-axis": ctrl.output_dq[1]
                    })
                
                torque_plot.add_data_point(elapsed, {
                    "Total torque": io.motor.kinematic.torque,
                    "bEMF U torque": io.motor.electrical.bemf_torques[0] * phase_currents[0],
                    "bEMF V torque": io.motor.electrical.bemf_torques[1] * phase_currents[1],
                    "bEMF W torque": io.motor.electrical.bemf_torques[2] * phase_currents[2]
                })
        
        # Update all plots
        angle_plot.update_plot()
        voltage_plot.update_plot()
        phase_current_plot.update_plot()
        current_plot.update_plot()
        output_plot.update_plot()
        torque_plot.update_plot()
        
        dpg.set_value(info_text, f"Velocity: {io.motor.kinematic.rotor_angular_velocity:.2f} rad/s\n\
Angle: {io.motor.kinematic.rotor_angle:.4f}\n\
Current update rate: {UPDATES_PER_FRAME / delta:.2f} Hz\n\
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
