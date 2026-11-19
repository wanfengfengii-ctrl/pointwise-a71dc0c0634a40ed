from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction
from math import floor

from phase.trials.rational import decode_rational, encode_rational


@dataclass(frozen=True)
class PhaseInterval:
    lower: Fraction
    upper: Fraction
    lower_closed: bool
    upper_closed: bool

    def __post_init__(self) -> None:
        if type(self.lower_closed) is not bool or type(self.upper_closed) is not bool:
            raise ValueError('interval boundary flags must be boolean')
        if not 0 <= self.lower <= self.upper <= 1 or self.upper == 1 and self.upper_closed:
            raise ValueError('phase interval outside [0,1)')
        if self.lower == self.upper and not (self.lower_closed and self.upper_closed):
            raise ValueError('empty phase interval')

    def contains(self, phase: Fraction) -> bool:
        return ((self.lower < phase or self.lower_closed and self.lower == phase)
                and (phase < self.upper or self.upper_closed and phase == self.upper))


def fold_mod_one(
    lower: Fraction, upper: Fraction, lower_closed: bool, upper_closed: bool,
) -> tuple[PhaseInterval, ...]:
    pieces = []
    for turn in range(floor(lower), floor(upper) + 1):
        low = max(lower, Fraction(turn))
        high = min(upper, Fraction(turn + 1))
        low_closed = low != lower or lower_closed
        high_closed = high < turn + 1 and (high != upper or upper_closed)
        if low < high or low == high and low_closed and high_closed:
            pieces.append(PhaseInterval(low - turn, high - turn, low_closed, high_closed))
    return tuple(pieces)


def normalize_phase_set(pieces: Iterable[PhaseInterval]) -> tuple[PhaseInterval, ...]:
    ordered = sorted(pieces, key=lambda item: (item.lower, not item.lower_closed, item.upper))
    combined: list[PhaseInterval] = []
    for item in ordered:
        if not combined:
            combined.append(item)
            continue
        previous = combined[-1]
        touches = previous.upper == item.lower and (previous.upper_closed or item.lower_closed)
        if item.lower > previous.upper or item.lower == previous.upper and not touches:
            combined.append(item)
            continue
        high = max(previous.upper, item.upper)
        high_closed = ((previous.upper == high and previous.upper_closed)
                       or (item.upper == high and item.upper_closed))
        combined[-1] = PhaseInterval(previous.lower, high, previous.lower_closed, high_closed)
    return tuple(combined)


def encode_phase_set(intervals: Iterable[PhaseInterval]) -> list:
    return [[encode_rational(item.lower), encode_rational(item.upper),
             item.lower_closed, item.upper_closed] for item in intervals]


def decode_phase_set(raw: object) -> tuple[PhaseInterval, ...]:
    if not isinstance(raw, list):
        raise ValueError('phase set must be a list')
    pieces = []
    for entry in raw:
        if not isinstance(entry, list) or len(entry) != 4:
            raise ValueError('invalid phase interval encoding')
        low, high, low_closed, high_closed = entry
        pieces.append(PhaseInterval(decode_rational(low), decode_rational(high), low_closed, high_closed))
    if tuple(pieces) != normalize_phase_set(pieces):
        raise ValueError('stored phase set is not in canonical order')
    return tuple(pieces)
