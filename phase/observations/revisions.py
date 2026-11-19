from dataclasses import dataclass
from fractions import Fraction

from phase.observations.arcs import ClosedArc
from phase.trials.identities import StationId, TrialId, require_id


@dataclass(frozen=True, order=True)
class ObservationKey:
    trial: TrialId
    station: StationId
    observation: str

    def __post_init__(self) -> None:
        require_id(self.trial, 'trial')
        require_id(self.station, 'station')
        require_id(self.observation, 'observation')


@dataclass(frozen=True, order=True)
class RevisionRef:
    key: ObservationKey
    number: int

    def __post_init__(self) -> None:
        if type(self.number) is not int or not 0 < self.number <= 2**63 - 1:
            raise ValueError('invalid revision number')


@dataclass(frozen=True)
class ObservationRevision:
    ref: RevisionRef
    parent: RevisionRef | None
    time: Fraction
    arc: ClosedArc


def first_revision(key: ObservationKey, time: Fraction, arc: ClosedArc) -> ObservationRevision:
    return ObservationRevision(RevisionRef(key, 1), None, time, arc)


def next_revision(parent: RevisionRef, time: Fraction, arc: ClosedArc) -> ObservationRevision:
    return ObservationRevision(RevisionRef(parent.key, parent.number + 1), parent, time, arc)
