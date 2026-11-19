from fractions import Fraction
import sqlite3

from phase.observations.arcs import ClosedArc, make_closed_arc
from phase.observations.revisions import (
    ObservationKey, ObservationRevision, RevisionRef, first_revision, next_revision,
)
from phase.storage import initialize, write_transaction
from phase.trials.rational import decode_rational, encode_rational


_SCHEMA = '''
CREATE TABLE IF NOT EXISTS observation_revisions (
    trial_id TEXT NOT NULL,
    station_id TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    parent INTEGER,
    observed_at TEXT NOT NULL,
    arc_start TEXT NOT NULL,
    arc_end TEXT NOT NULL,
    PRIMARY KEY (trial_id, station_id, observation_id, revision),
    FOREIGN KEY (trial_id, station_id, observation_id, parent)
        REFERENCES observation_revisions(trial_id, station_id, observation_id, revision)
);
CREATE TABLE IF NOT EXISTS observation_heads (
    trial_id TEXT NOT NULL,
    station_id TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    PRIMARY KEY (trial_id, station_id, observation_id),
    FOREIGN KEY (trial_id, station_id, observation_id, revision)
        REFERENCES observation_revisions(trial_id, station_id, observation_id, revision)
);
'''


def _key_columns(key: ObservationKey) -> tuple[str, str, str]:
    return key.trial, key.station, key.observation


class ObservationLedger:
    def __init__(self, connection: sqlite3.Connection):
        self._db = connection
        initialize(connection, _SCHEMA)

    def current_ref(self, key: ObservationKey) -> RevisionRef | None:
        row = self._db.execute(
            '''SELECT revision FROM observation_heads
               WHERE trial_id = ? AND station_id = ? AND observation_id = ?''',
            _key_columns(key),
        ).fetchone()
        return None if row is None else RevisionRef(key, row[0])

    def _save_revision(self, revision: ObservationRevision) -> None:
        parent = None if revision.parent is None else revision.parent.number
        self._db.execute(
            'INSERT INTO observation_revisions VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (*_key_columns(revision.ref.key), revision.ref.number, parent,
             encode_rational(revision.time), encode_rational(revision.arc.start),
             encode_rational(revision.arc.end)),
        )

    def insert_first(self, key: ObservationKey, time: Fraction, arc: ClosedArc) -> ObservationRevision:
        revision = first_revision(key, time, arc)
        with write_transaction(self._db):
            if self.current_ref(key) is not None:
                raise ValueError('observation already recorded')
            self._save_revision(revision)
            self._db.execute(
                'INSERT INTO observation_heads VALUES (?, ?, ?, ?)',
                (*_key_columns(key), revision.ref.number),
            )
        return revision

    def append_from_current(
        self, parent: RevisionRef, time: Fraction, arc: ClosedArc
    ) -> ObservationRevision:
        with write_transaction(self._db):
            if self.current_ref(parent.key) != parent:
                raise ValueError('parent revision is missing or no longer current')
            revision = next_revision(parent, time, arc)
            self._save_revision(revision)
            self._db.execute(
                '''UPDATE observation_heads SET revision = ?
                   WHERE trial_id = ? AND station_id = ? AND observation_id = ?''',
                (revision.ref.number, *_key_columns(parent.key)),
            )
        return revision

    def read_revision(self, reference: RevisionRef) -> ObservationRevision | None:
        row = self._db.execute(
            '''SELECT parent, observed_at, arc_start, arc_end FROM observation_revisions
               WHERE trial_id = ? AND station_id = ? AND observation_id = ? AND revision = ?''',
            (*_key_columns(reference.key), reference.number),
        ).fetchone()
        if row is None:
            return None
        parent, time, start, end = row
        return ObservationRevision(
            reference, None if parent is None else RevisionRef(reference.key, parent),
            decode_rational(time), make_closed_arc(decode_rational(start), decode_rational(end)),
        )
