from collections.abc import Iterable

from phase.observations.ledger import ObservationLedger
from phase.observations.revisions import RevisionRef
from phase.station.artifact import StationArtifact
from phase.station.calibration import compile_station_evidence
from phase.station.ledger import StationLedger
from phase.station.selection import resolve_selection
from phase.trials.registry import TrialRegistry


def issue(
    registry: TrialRegistry, observations: ObservationLedger, issues: StationLedger,
    trial_id: str, station: str, references: Iterable[RevisionRef],
) -> StationArtifact:
    selection = resolve_selection(registry, observations, trial_id, station, references)
    evidence = compile_station_evidence(selection)
    return issues.issue_artifact(
        selection.trial.trial_id, selection.source,
        tuple(revision.ref for revision in selection.revisions), evidence,
    )
