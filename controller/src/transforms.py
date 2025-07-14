from typing import NamedTuple
import math

class ClarkeOutput(NamedTuple):
    """
    The output of the Clarke transform.
    Alpha and beta are transformed components of the three-phase currents in the stator reference frame.
    """
    # X-axis component (alpha)
    alpha: float
    # Y-axis component (beta)
    beta: float

class ParkOutput(NamedTuple):
    """
    The output of the Park transform.
    D-axis and Q-axis components are transformed components of the stator currents in the rotor reference frame.
    """
    # D-axis component (parallel to the rotor's magnetic field)
    d: float
    # Q-axis component (perpendicular to the rotor's magnetic field, responsible for torque)
    q: float

def clarke_transform(iu: float, iv: float, iw: float) -> ClarkeOutput:
    """
    Perform the Clarke transformation on three-phase currents.
    Converts three-phase currents (lu, lv, and lw) into two-phase orthogonal components
    relative to the stator reference frame (alpha and beta).
    """
    alpha = iu - iv/2 - iw/2
    beta = math.sqrt(3)/2 * iv - math.sqrt(3)/2 * iw
    return ClarkeOutput(alpha, beta)

def park_transform(alpha_beta: ClarkeOutput, theta: float) -> ParkOutput:
    """
    Perform the Park transformation on two-phase orthogonal components.
    Converts the Clarke output (alpha and beta) into D-axis and Q-axis components
    relative to the rotor reference frame, given the rotor angle theta.
    """
    cos = math.cos(theta)
    sin = math.sin(theta)
    d = alpha_beta.alpha * cos + alpha_beta.beta * sin
    q = -alpha_beta.alpha * sin + alpha_beta.beta * cos
    return ParkOutput(d, q)

def inverse_park_transform(dq: ParkOutput, theta: float) -> ClarkeOutput:
    """
    Perform the inverse Park transformation on D-axis and Q-axis components.
    Converts the D-axis and Q-axis components back into Clarke output (alpha and beta)
    relative to the stator reference frame, given the rotor angle theta.
    """
    cos = math.cos(theta)
    sin = math.sin(theta)
    alpha = dq.d * cos - dq.q * sin
    beta = dq.d * sin + dq.q * cos
    return ClarkeOutput(alpha, beta)

def inverse_clarke_transform(clarke: ClarkeOutput) -> tuple[float, float, float]:
    """
    Perform the inverse Clarke transformation on two-phase orthogonal components.
    Converts the Clarke output (alpha and beta) back into three-phase components
    (lu, lv, and lw) relative to the stator reference frame.
    """
    iu = clarke.alpha + clarke.beta / math.sqrt(3)
    iv = -clarke.alpha / 2 + clarke.beta * math.sqrt(3) / 2
    iw = -clarke.alpha / 2 - clarke.beta * math.sqrt(3) / 2
    return iu, iv, iw