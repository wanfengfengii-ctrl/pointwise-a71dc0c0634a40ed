from phase.observations.arcs import make_closed_arc
from phase.observations.ledger import ObservationLedger
from phase.observations.revisions import ObservationKey, ObservationRevision, RevisionRef
from phase.trials.identities import TrialId
from phase.trials.rational import RationalInput
from phase.trials.registry import TrialRegistry
from phase.trials.stations import require_trial_station


def record_arc(
    registry: TrialRegistry, ledger: ObservationLedger, trial_id: str, station: str,
    observation: str, time: RationalInput, start: RationalInput, end: RationalInput,
) -> ObservationRevision:
    trial = registry.get_trial(trial_id)
    source = require_trial_station(trial.stations, station)
    key = ObservationKey(TrialId(trial_id), source.station, observation)
    timestamp = trial.domain.require_time(time)
    return ledger.insert_first(key, timestamp, make_closed_arc(start, end))


def correct(
    registry: TrialRegistry, ledger: ObservationLedger, key: ObservationKey, parent: RevisionRef,
    time: RationalInput, start: RationalInput, end: RationalInput,
) -> ObservationRevision:
    if not isinstance(parent, RevisionRef) or parent.key != key:
        raise ValueError('parent revision is for another observation')
    trial = registry.get_trial(key.trial)
    require_trial_station(trial.stations, key.station)
    timestamp = trial.domain.require_time(time)
    return ledger.append_from_current(parent, timestamp, make_closed_arc(start, end))
