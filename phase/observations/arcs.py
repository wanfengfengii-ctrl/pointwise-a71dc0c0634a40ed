from dataclasses import dataclass
from fractions import Fraction

from phase.trials.rational import RationalInput, parse_rational


@dataclass(frozen=True)
class ClosedArc:
    start: Fraction
    end: Fraction

    def crosses_zero(self) -> bool:
        return self.start > self.end

    def is_tick(self) -> bool:
        return self.start == self.end


def make_closed_arc(start: RationalInput, end: RationalInput) -> ClosedArc:
    first = parse_rational(start)
    last = parse_rational(end)
    if not (0 <= first < 1 and 0 <= last < 1):
        raise ValueError('phase endpoint outside [0,1)')
    return ClosedArc(first, last)
