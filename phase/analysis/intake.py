from phase.analysis.catalog import AcceptedCatalog
from phase.station.artifact import decode_artifact
from phase.trials.registry import TrialRegistry
from phase.trials.stations import StationSource, verify_station_source


def accept(
    registry: TrialRegistry, catalog: AcceptedCatalog, payload: str, submitted: StationSource,
) -> str:
    artifact = decode_artifact(payload)
    trial = registry.get_trial(artifact.trial_id)
    source = verify_station_source(trial.stations, artifact.source, submitted)
    for clause in artifact.evidence.clauses:
        trial.domain.require_time(clause.time)
    return catalog.store(artifact, source)
