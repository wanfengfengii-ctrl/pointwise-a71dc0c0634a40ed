from dataclasses import dataclass
from fractions import Fraction

from phase.trials.rational import RationalInput, parse_rational


@dataclass(frozen=True)
class TrialDomain:
    start: Fraction
    end: Fraction
    drift_low: Fraction
    drift_high: Fraction

    def require_time(self, value: RationalInput) -> Fraction:
        time = parse_rational(value)
        if not self.start <= time <= self.end:
            raise ValueError('time outside trial domain')
        return time


def make_trial_domain(time_bounds, drift_bounds) -> TrialDomain:
    for bounds in (time_bounds, drift_bounds):
        if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
            raise ValueError('expected two endpoints for each trial bound')
    start, end = map(parse_rational, time_bounds)
    low, high = map(parse_rational, drift_bounds)
    if not 0 <= start <= end <= 4:
        raise ValueError('unsupported trial time domain')
    if not -Fraction(1, 4) <= low <= high <= Fraction(1, 4):
        raise ValueError('unsupported trial drift budget')
    return TrialDomain(start, end, low, high)
