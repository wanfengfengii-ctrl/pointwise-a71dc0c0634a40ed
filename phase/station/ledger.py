from dataclasses import replace
from hashlib import sha256
import sqlite3

from phase.observations.revisions import RevisionRef
from phase.station.artifact import (
    StationArtifact, decode_artifact, encode_artifact, same_artifact_content,
)
from phase.station.evidence import StationEvidence
from phase.storage import initialize, write_transaction
from phase.trials.identities import TrialId, require_id
from phase.trials.stations import StationSource


_SCHEMA = '''
CREATE TABLE IF NOT EXISTS station_issues (
    artifact_id TEXT PRIMARY KEY,
    package TEXT NOT NULL
);
'''


class StationLedger:
    def __init__(self, connection: sqlite3.Connection):
        self._db = connection
        initialize(connection, _SCHEMA)

    def issue_artifact(
        self, trial: TrialId, source: StationSource, revisions: tuple[RevisionRef, ...],
        evidence: StationEvidence,
    ) -> StationArtifact:
        if any(ref.key.trial != trial or ref.key.station != source.station for ref in revisions):
            raise ValueError('station package revision scope mismatch')
        draft = StationArtifact('pending', trial, source, revisions, evidence)
        digest = sha256(encode_artifact(draft).encode('utf-8')).hexdigest()
        artifact = replace(draft, artifact_id=f'ST-{digest}')
        package = encode_artifact(artifact)
        # Apply the same structural checks to locally issued and imported payloads.
        decode_artifact(package)
        with write_transaction(self._db):
            existing = self.read_artifact(artifact.artifact_id)
            if existing is None:
                self._db.execute(
                    'INSERT INTO station_issues VALUES (?, ?)', (artifact.artifact_id, package)
                )
            elif not same_artifact_content(existing, artifact):
                raise ValueError('station package number conflicts with an existing issue')
        return artifact

    def read_artifact(self, artifact_id: str) -> StationArtifact | None:
        require_id(artifact_id, 'artifact')
        row = self._db.execute(
            'SELECT package FROM station_issues WHERE artifact_id = ?', (artifact_id,)
        ).fetchone()
        return None if row is None else decode_artifact(row[0])
