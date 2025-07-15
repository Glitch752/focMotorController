from dataclasses import dataclass

@dataclass
class MotorElectricalState:
    phase_currents: tuple[float, float, float] = (0, 0, 0)
    """The motor phase currents in amps"""
    
    bemf_voltages: tuple[float, float, float] = (0, 0, 0)
    """The motor phase back EMFs in volts"""
    
    bemf_torques: tuple[float, float, float] = (0, 0, 0)
    """The torques from the back EMFs per phase in Nm/A"""