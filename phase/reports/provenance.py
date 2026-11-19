from collections.abc import Iterable
from dataclasses import dataclass

from phase.analysis.catalog import AcceptedArtifact
from phase.observations.revisions import RevisionRef
from phase.station.artifact import decode_revision_refs, encode_revision_refs
from phase.trials.identities import StationId, TrialId, require_id
from phase.trials.registry import RegisteredTrial
from phase.trials.stations import StationSource, verify_station_source


@dataclass(frozen=True)
class ArtifactProvenance:
    artifact_id: str
    source: StationSource
    revisions: tuple[RevisionRef, ...]


def capture_provenance(
    trial: RegisteredTrial, accepted: Iterable[AcceptedArtifact],
) -> tuple[ArtifactProvenance, ...]:
    result = []
    seen = set()
    for entry in accepted:
        artifact = entry.artifact
        if artifact.trial_id != trial.trial_id or artifact.artifact_id in seen:
            raise ValueError('invalid fixed report package selection')
        source = verify_station_source(trial.stations, artifact.source, entry.source)
        seen.add(artifact.artifact_id)
        result.append(ArtifactProvenance(artifact.artifact_id, source, artifact.revisions))
    if not result:
        raise ValueError('missing report provenance')
    return tuple(result)


def encode_provenance(items: Iterable[ArtifactProvenance]) -> list:
    return [
        {'artifact_id': item.artifact_id, 'station': item.source.station,
         'source': item.source.source, 'revisions': encode_revision_refs(item.revisions)}
        for item in items
    ]


def decode_provenance(raw: object, trial: TrialId) -> tuple[ArtifactProvenance, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError('missing stored provenance')
    result = []
    for item in raw:
        if not isinstance(item, dict) or set(item) != {'artifact_id', 'station', 'source', 'revisions'}:
            raise ValueError('invalid stored provenance')
        source = StationSource(StationId(item['station']), item['source'])
        result.append(ArtifactProvenance(
            require_id(item['artifact_id'], 'artifact'), source,
            decode_revision_refs(item['revisions'], trial, source.station),
        ))
    return tuple(result)
