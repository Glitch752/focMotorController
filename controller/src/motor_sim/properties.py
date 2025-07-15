
from dataclasses import dataclass, field
import math
from typing import NamedTuple, cast

from ..util import clamp

BackEMFCoeffs = tuple[float, float, float, float, float]

class PhaseBackEMFs(NamedTuple):
    bemf_torques: tuple[float, float, float]
    """The torques from the back EMFs per phase in Nm/A"""
    phase_bemf: tuple[float, float, float]
    """The back EMFs per phase in volts"""

@dataclass
class MotorProperties:
    pole_pairs: int
    """The number of pole pairs in the motor."""
    
    rotor_inertia: float = 0.00015
    """The rotor inertia in kg*m^2."""
    
    phase_inductance: float = 1e-3
    """The phase inductance in henries."""
    
    phase_resistance: float = 1.0
    """The phase resistance in ohms."""
    
    bemf_constant: float = 0.01
    """
    The motor's K_e in V/(rad/s). Mathematically, this is the same as the torque constant K_t.
    """
    
    normed_bemf_coeffs: BackEMFCoeffs = (1, 0, 0, 0, 0)
    """
    Represents the motor's torque-current curve; odd coefficients of the sine fourier expansion.
    If the motor has a sinusoidal backemf waveform, this should be (1, 0, 0, 0, 0).  
    Note that in the [source](https://github.com/markisus/motor_sim/blob/master/simulator/motor_state.h#L36) from
    the simulation I'm referencing, this isn't a normalized curve at all (?) and instead represents the true
    bEMF waveform. I've instead adapted it to be unitless and have a separate K_e constant.
    """
    
    cogging_torque_map: list[float] = field(default_factory=lambda: [0] * 3600)
    """
    Cogging torque of the motor across its rotational range. Cogging torque is a
    (typically undesireable) torque from the interaction of the stator's permanent magnets
    with the rotor.  
    Cogging torque is typically only 1-5% of the motor's stall torque, so it's not
    extremely significant.
    """
    
    viscous_friction: float = 0.0001
    """
    The viscous friction of the motor in Nm/(rad/s). Viscous friction is friction
    proportional to speed.
    """
    
    coulomb_frinction: float = 0.001
    """
    The coulomb friction of the motor in Nm. Coulomb friction is a constant
    friction that exists regardless of speed.
    """
    
    vbus: float = 12
    """
    The bus voltage of the motor in volts. In a real motor, this is a "reference voltage"
    and the controller should compensate for voltage drop through SVM, but in this simulation
    we just assume the bus voltage is constant and equal to this value.
    """
    
    def get_cogging_torque_at_rotor_angle(self, theta: float) -> float:
        """Get the cogging torque at a specific rotor angle in radians."""
        items = len(self.cogging_torque_map)
        normalized_angle = items * clamp(theta / (2 * math.pi), 0, 1)
        integral_part = int(normalized_angle)
        fractional_part = normalized_angle - integral_part
        t1 = self.cogging_torque_map[integral_part]
        t2 = self.cogging_torque_map[(integral_part + 1) % items]
        return t1 * (1 - fractional_part) + t2 * fractional_part

    def mechanical_to_electrical_angle(self, mechanical_angle: float) -> float:
        return (mechanical_angle * self.pole_pairs) % (2 * math.pi)
    
    def get_normalized_backemf(self, electrical_angle: float) -> float:
        sine_series: list[float] = [0, 0, 0, 0, 0]
        terms = 5
        
        # This is a cheaper way to compute the odd sine series at multiples of the given angle
        # https://trans4mind.com/personal_development/mathematics/trigonometry/multipleAnglesRecursiveFormula.htm#Recursive_Formula
        sin_angle: float = math.sin(electrical_angle)
        cos_angle: float = math.cos(electrical_angle)

        sa = 0
        sb = sin_angle

        for i in range(terms - 1):
            sine_series[i] = sb
            
            sa = 2 * cos_angle * sb - sa
            (sb, sa) = (sa, sb)
            # Advance twice to get odd multiples
            sa = 2 * cos_angle * sb - sa
            (sb, sa) = (sa, sb)
        
        sine_series[terms - 1] = sb
        
        # Compute the dot product between the sine series and backemf coefficients
        return sum(sine_series[i] * self.normed_bemf_coeffs[i] for i in range(len(self.normed_bemf_coeffs)))
    
    def get_phase_normalized_backemfs(self, electrical_angle: float) -> tuple[float, float, float]:
        return (
            self.get_normalized_backemf(electrical_angle),
            self.get_normalized_backemf(electrical_angle - 2 * math.pi / 3),
            self.get_normalized_backemf(electrical_angle - 4 * math.pi / 3)
        )
    
    def get_phase_backemfs(self, electrical_angle: float, electrical_angular_vel: float) -> PhaseBackEMFs:
        normalized_bemfs = self.get_phase_normalized_backemfs(electrical_angle)
        
        bemf_torques = cast(tuple[float, float, float],
            tuple(bemf * self.bemf_constant for bemf in normalized_bemfs)
        )
        
        phase_bemfs = cast(tuple[float, float, float],
            tuple(bemf  * electrical_angular_vel for bemf in bemf_torques)
        )
    
        return PhaseBackEMFs(
            bemf_torques=bemf_torques,
            phase_bemf=phase_bemfs
        )
    
    def get_friction_torque(self, velocity: float) -> float:
        return -(self.viscous_friction * velocity + math.copysign(self.coulomb_frinction, velocity))

REV_NEO_PROPS = MotorProperties(
    pole_pairs=7,
    # TODO: measure inertia, phase inductance and resistance, and backemf
    # Empirical Kv = 473 RPM/V; Ke = 1/Kv * 60/(2*pi)
    bemf_constant = 1/473 * 60 / (2*math.pi),
    # Rough approximations taken from https://www.chiefdelphi.com/t/brushless-motor-controller-tester/392593/23
    # Phase inductance is ~10 mH
    phase_inductance = 0.01,
    # Phase resistance is ~30 mOhm
    phase_resistance = 0.03
)