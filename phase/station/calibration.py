from fractions import Fraction
from math import ceil

from phase.observations.arcs import ClosedArc
from phase.station.evidence import CalibrationClause, LinearBound, StationEvidence
from phase.station.selection import FrozenSelection


def _lifted_segments(
    arc: ClosedArc, minimum: Fraction, supremum: Fraction,
) -> list[tuple[Fraction, Fraction]]:
    segments = ((arc.start, arc.end),)
    if arc.crosses_zero():
        segments = ((Fraction(0), arc.end), (arc.start, Fraction(1)))

    lifted = []
    for low, high in segments:
        # low + turn must be strictly below the domain supremum.
        for turn in range(ceil(minimum - high), ceil(supremum - low)):
            lifted.append((max(minimum, low + turn), min(supremum, high + turn)))

    merged: list[tuple[Fraction, Fraction]] = []
    for low, high in sorted(lifted):
        if merged and low <= merged[-1][1]:
            previous_low, previous_high = merged[-1]
            merged[-1] = previous_low, max(previous_high, high)
        else:
            merged.append((low, high))
    return merged


def compile_station_evidence(selection: FrozenSelection) -> StationEvidence:
    domain = selection.trial.domain
    clauses = []
    for revision in selection.revisions:
        time = domain.require_time(revision.time)
        minimum = time * domain.drift_low
        supremum = 1 + time * domain.drift_high
        strips = tuple(
            (LinearBound(Fraction(1), time, high), LinearBound(Fraction(-1), -time, -low))
            for low, high in _lifted_segments(revision.arc, minimum, supremum)
        )
        clauses.append(CalibrationClause(strips))
    return StationEvidence(tuple(clauses))
