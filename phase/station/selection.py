from collections.abc import Iterable
from dataclasses import dataclass

from phase.observations.ledger import ObservationLedger
from phase.observations.revisions import ObservationRevision, RevisionRef
from phase.station.evidence import MAX_OBSERVATIONS
from phase.trials.registry import RegisteredTrial, TrialRegistry
from phase.trials.stations import StationSource, require_trial_station


@dataclass(frozen=True)
class FrozenSelection:
    trial: RegisteredTrial
    source: StationSource
    revisions: tuple[ObservationRevision, ...]


def resolve_selection(
    registry: TrialRegistry, ledger: ObservationLedger, trial_id: str, station: str,
    references: Iterable[RevisionRef],
) -> FrozenSelection:
    trial = registry.get_trial(trial_id)
    source = require_trial_station(trial.stations, station)
    refs = tuple(references)
    if not 1 <= len(refs) <= MAX_OBSERVATIONS:
        raise ValueError('select between one and six revisions')
    if any(not isinstance(ref, RevisionRef) for ref in refs):
        raise ValueError('select explicit revision references')
    if len(set(refs)) != len(refs):
        raise ValueError('repeated revision reference')

    revisions = []
    for ref in sorted(refs):
        if ref.key.trial != trial.trial_id or ref.key.station != source.station:
            raise ValueError('a station package must use one station and one trial')
        revision = ledger.read_revision(ref)
        if revision is None:
            raise ValueError(f'unknown observation revision {ref!r}')
        revisions.append(revision)
    return FrozenSelection(trial, source, tuple(revisions))
