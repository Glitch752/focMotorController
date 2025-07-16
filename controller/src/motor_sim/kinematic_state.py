from dataclasses import dataclass

@dataclass
class MotorKinematicState:
    rotor_angle: float = 0
    """The rotor angle in radians."""
    
    rotor_angular_velocity: float = 0
    """The rotor angular velocity in rad/s."""
    
    rotor_angular_acceleration: float = 0
    """The rotor angular acceleration in rad/s^2"""

    electromagnetic_torque: float = 0
    """The contribution to the rotor torque from electromagnetism."""
    
    torque: float = 0
    """The torque applied to the rotor in Nm."""