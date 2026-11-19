from dataclasses import dataclass
import sqlite3

from phase.station.artifact import (
    StationArtifact, decode_artifact, encode_artifact, same_artifact_content,
)
from phase.storage import initialize, write_transaction
from phase.trials.identities import StationId, require_id
from phase.trials.stations import StationSource


_SCHEMA = '''
CREATE TABLE IF NOT EXISTS accepted_artifacts (
    artifact_id TEXT PRIMARY KEY,
    station_id TEXT NOT NULL,
    source TEXT NOT NULL,
    package TEXT NOT NULL
);
'''


@dataclass(frozen=True)
class AcceptedArtifact:
    artifact: StationArtifact
    source: StationSource


class AcceptedCatalog:
    def __init__(self, connection: sqlite3.Connection):
        self._db = connection
        initialize(connection, _SCHEMA)

    def store(self, artifact: StationArtifact, source: StationSource) -> str:
        if artifact.source != source:
            raise ValueError('received source differs from station package')
        with write_transaction(self._db):
            existing = self.load(artifact.artifact_id)
            if existing is None:
                self._db.execute(
                    'INSERT INTO accepted_artifacts VALUES (?, ?, ?, ?)',
                    (artifact.artifact_id, source.station, source.source, encode_artifact(artifact)),
                )
            elif existing.source != source or not same_artifact_content(existing.artifact, artifact):
                raise ValueError('artifact number is already bound to different content')
        return artifact.artifact_id

    def load(self, artifact_id: str) -> AcceptedArtifact | None:
        require_id(artifact_id, 'artifact')
        row = self._db.execute(
            'SELECT station_id, source, package FROM accepted_artifacts WHERE artifact_id = ?',
            (artifact_id,),
        ).fetchone()
        if row is None:
            return None
        station, source, package = row
        artifact = decode_artifact(package)
        if artifact.artifact_id != artifact_id:
            raise ValueError('stored package number differs from its catalog key')
        return AcceptedArtifact(artifact, StationSource(StationId(station), source))
