from dataclasses import dataclass
from fractions import Fraction

from phase.trials.rational import decode_rational, encode_rational


MAX_OBSERVATIONS = 6
# Each of the two seam segments can meet at most four lifted turns in V1.
_MAX_ALTERNATIVES = 8


@dataclass(frozen=True)
class LinearBound:
    p: Fraction
    d: Fraction
    limit: Fraction

    def excess(self, point: tuple[Fraction, Fraction]) -> Fraction:
        phase, drift = point
        return self.p * phase + self.d * drift - self.limit


@dataclass(frozen=True)
class CalibrationClause:
    alternatives: tuple[tuple[LinearBound, LinearBound], ...]

    @property
    def time(self) -> Fraction:
        return self.alternatives[0][0].d


@dataclass(frozen=True)
class StationEvidence:
    clauses: tuple[CalibrationClause, ...]


def encode_evidence(evidence: StationEvidence) -> list:
    return [
        [[[encode_rational(bound.p), encode_rational(bound.d), encode_rational(bound.limit)]
          for bound in strip] for strip in clause.alternatives]
        for clause in evidence.clauses
    ]


def _decode_bound(raw: object) -> LinearBound:
    if not isinstance(raw, list) or len(raw) != 3:
        raise ValueError('invalid linear bound')
    return LinearBound(*(decode_rational(item) for item in raw))


def _decode_clause(raw: object) -> CalibrationClause:
    if not isinstance(raw, list) or not 1 <= len(raw) <= _MAX_ALTERNATIVES:
        raise ValueError('invalid calibration alternatives')
    strips = []
    for pair in raw:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError('a calibration strip needs two bounds')
        upper, lower = map(_decode_bound, pair)
        if (upper.p != 1 or lower.p != -1 or upper.d != -lower.d
                or not 0 <= upper.d <= 4 or not -1 <= -lower.limit <= upper.limit <= 2):
            raise ValueError('invalid calibration strip')
        if strips and upper.d != strips[0][0].d:
            raise ValueError('a calibration clause must use one observation time')
        strips.append((upper, lower))
    return CalibrationClause(tuple(strips))


def decode_evidence(raw: object) -> StationEvidence:
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_OBSERVATIONS:
        raise ValueError('invalid calibration evidence')
    return StationEvidence(tuple(map(_decode_clause, raw)))
