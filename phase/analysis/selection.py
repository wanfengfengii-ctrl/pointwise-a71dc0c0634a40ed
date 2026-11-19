from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction

from phase.analysis.catalog import AcceptedArtifact, AcceptedCatalog
from phase.station.evidence import MAX_OBSERVATIONS
from phase.trials.identities import require_id
from phase.trials.rational import RationalInput
from phase.trials.registry import RegisteredTrial, TrialRegistry


@dataclass(frozen=True)
class ForecastSelection:
    trial: RegisteredTrial
    time: Fraction
    artifacts: tuple[AcceptedArtifact, ...]


def resolve_forecast_selection(
    registry: TrialRegistry, catalog: AcceptedCatalog, artifact_ids: Iterable[str], time: RationalInput,
) -> ForecastSelection:
    if isinstance(artifact_ids, str):
        raise ValueError('expected a collection of artifact numbers')
    ids = tuple(require_id(value, 'artifact') for value in artifact_ids)
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('select distinct fixed station packages')

    artifacts = []
    for artifact_id in sorted(ids):
        accepted = catalog.load(artifact_id)
        if accepted is None:
            raise ValueError(f'unknown accepted package {artifact_id!r}')
        artifacts.append(accepted)
    trial_id = artifacts[0].artifact.trial_id
    if any(item.artifact.trial_id != trial_id for item in artifacts):
        raise ValueError('forecast cannot mix trials')
    if sum(len(item.artifact.revisions) for item in artifacts) > MAX_OBSERVATIONS:
        raise ValueError('forecast may use at most six observation revisions')
    trial = registry.get_trial(trial_id)
    return ForecastSelection(trial, trial.domain.require_time(time), tuple(artifacts))
