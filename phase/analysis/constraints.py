from dataclasses import dataclass
from fractions import Fraction
from typing import NamedTuple

from phase.analysis.selection import ForecastSelection
from phase.station.evidence import LinearBound


Point = tuple[Fraction, Fraction]


@dataclass(frozen=True)
class FeasibleRegion:
    # Convex closure in boundary order. One or two vertices denote a point or segment.
    # The trial domain excludes the face p = 1 from every region.
    vertices: tuple[Point, ...]


class LinearImage(NamedTuple):
    lower: Fraction
    upper: Fraction
    lower_closed: bool
    upper_closed: bool


def _intersection(left: Point, right: Point, before: Fraction, after: Fraction) -> Point:
    fraction = before / (before - after)
    return (left[0] + fraction * (right[0] - left[0]),
            left[1] + fraction * (right[1] - left[1]))


def _clip(vertices: tuple[Point, ...], bound: LinearBound) -> tuple[Point, ...]:
    result = []
    for left, right in zip(vertices, vertices[1:] + vertices[:1]):
        before = bound.excess(left)
        after = bound.excess(right)
        if before < 0 < after or after < 0 < before:
            result.append(_intersection(left, right, before, after))
        if after <= 0:
            result.append(right)
    return tuple(dict.fromkeys(result))


def solve_joint_constraints(selection: ForecastSelection) -> tuple[FeasibleRegion, ...]:
    domain = selection.trial.domain
    low, high = domain.drift_low, domain.drift_high
    zero, one = Fraction(0), Fraction(1)
    corners = ((zero, low), (one, low), (one, high), (zero, high))
    pieces = [tuple(dict.fromkeys(corners))]
    for accepted in selection.artifacts:
        for clause in accepted.artifact.evidence.clauses:
            following = []
            for vertices in pieces:
                for upper, lower in clause.alternatives:
                    clipped = _clip(_clip(vertices, upper), lower)
                    # A nonempty face entirely on p = 1 has no admissible point.
                    if any(point[0] < 1 for point in clipped):
                        following.append(clipped)
            if not following:
                return ()
            pieces = following
    return tuple(FeasibleRegion(piece) for piece in pieces)


def project_linear_image(region: FeasibleRegion, time: Fraction) -> LinearImage:
    values = [(p + time * drift, p < 1) for p, drift in region.vertices]
    low = min(value for value, _ in values)
    high = max(value for value, _ in values)
    # An extreme is attained exactly when its face has an admissible vertex.
    return LinearImage(
        low, high,
        any(value == low and admissible for value, admissible in values),
        any(value == high and admissible for value, admissible in values),
    )
