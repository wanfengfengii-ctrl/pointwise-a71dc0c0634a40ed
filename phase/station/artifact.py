from dataclasses import dataclass
import json

from phase.observations.revisions import ObservationKey, RevisionRef
from phase.station.evidence import StationEvidence, decode_evidence, encode_evidence
from phase.trials.identities import StationId, TrialId, require_id
from phase.trials.stations import StationSource


_FIELDS = {'version', 'artifact_id', 'trial_id', 'station', 'source', 'revisions', 'evidence'}


@dataclass(frozen=True)
class StationArtifact:
    artifact_id: str
    trial_id: TrialId
    source: StationSource
    revisions: tuple[RevisionRef, ...]
    evidence: StationEvidence


def encode_revision_refs(revisions: tuple[RevisionRef, ...]) -> list:
    return [[ref.key.observation, ref.number] for ref in revisions]


def decode_revision_refs(raw: object, trial: TrialId, station: StationId) -> tuple[RevisionRef, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError('missing fixed revision references')
    refs = []
    for pair in raw:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError('invalid fixed revision reference')
        observation, number = pair
        refs.append(RevisionRef(ObservationKey(trial, station, observation), number))
    if len(set(refs)) != len(refs):
        raise ValueError('repeated fixed revision reference')
    return tuple(refs)


def encode_artifact(artifact: StationArtifact) -> str:
    document = {
        'version': 1,
        'artifact_id': artifact.artifact_id,
        'trial_id': artifact.trial_id,
        'station': artifact.source.station,
        'source': artifact.source.source,
        'revisions': encode_revision_refs(artifact.revisions),
        'evidence': encode_evidence(artifact.evidence),
    }
    return json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def _unique_object(pairs: list) -> dict:
    document = dict(pairs)
    if len(document) != len(pairs):
        raise ValueError('duplicate station package field')
    return document


def decode_artifact(payload: str) -> StationArtifact:
    if not isinstance(payload, str):
        raise ValueError('station package must be JSON text')
    doc = json.loads(payload, object_pairs_hook=_unique_object)
    if (not isinstance(doc, dict) or set(doc) != _FIELDS
            or type(doc['version']) is not int or doc['version'] != 1):
        raise ValueError('expected a V1 station package')
    artifact_id = require_id(doc['artifact_id'], 'artifact')
    trial = TrialId(require_id(doc['trial_id'], 'trial'))
    source = StationSource(StationId(doc['station']), doc['source'])
    evidence = decode_evidence(doc['evidence'])
    revisions = decode_revision_refs(doc['revisions'], trial, source.station)
    if len(revisions) != len(evidence.clauses):
        raise ValueError('station evidence and revision references differ in count')
    return StationArtifact(artifact_id, trial, source, revisions, evidence)


def same_artifact_content(first: StationArtifact, second: StationArtifact) -> bool:
    return first == second
