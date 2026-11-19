from dataclasses import dataclass
from fractions import Fraction
import json
import sqlite3

from phase.analysis.phase_set import PhaseInterval, decode_phase_set, encode_phase_set
from phase.reports.provenance import ArtifactProvenance, decode_provenance, encode_provenance
from phase.storage import initialize, write_transaction
from phase.trials.identities import TrialId
from phase.trials.rational import decode_rational, encode_rational


_SCHEMA = '''
CREATE TABLE IF NOT EXISTS reports (
    report_id INTEGER PRIMARY KEY,
    trial_id TEXT NOT NULL,
    forecast_time TEXT NOT NULL,
    phases TEXT NOT NULL,
    provenance TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS issue_receipts (
    report_id INTEGER PRIMARY KEY REFERENCES reports(report_id),
    receipt_id TEXT NOT NULL UNIQUE
);
'''


@dataclass(frozen=True)
class IssueReceipt:
    report_id: int
    receipt_id: str


@dataclass(frozen=True)
class PublishedReport:
    report_id: int
    trial_id: TrialId
    time: Fraction
    phases: tuple[PhaseInterval, ...]
    provenance: tuple[ArtifactProvenance, ...]
    receipt: IssueReceipt


class ReportLedger:
    def __init__(self, connection: sqlite3.Connection):
        self._db = connection
        initialize(connection, _SCHEMA)

    def commit_report(
        self, trial_id: TrialId, time: Fraction, phases: tuple[PhaseInterval, ...],
        provenance: tuple[ArtifactProvenance, ...],
    ) -> PublishedReport:
        phase_json = json.dumps(encode_phase_set(phases), separators=(',', ':'))
        provenance_json = json.dumps(encode_provenance(provenance), ensure_ascii=False, separators=(',', ':'))
        with write_transaction(self._db):
            row = self._db.execute(
                '''INSERT INTO reports (trial_id, forecast_time, phases, provenance)
                   VALUES (?, ?, ?, ?)''',
                (trial_id, encode_rational(time), phase_json, provenance_json),
            )
            report_id = row.lastrowid
            receipt = IssueReceipt(report_id, f'R-{report_id:06d}')
            self._db.execute(
                'INSERT INTO issue_receipts VALUES (?, ?)', (report_id, receipt.receipt_id)
            )
        return PublishedReport(report_id, trial_id, time, phases, provenance, receipt)

    def load_report(self, report_id: int) -> PublishedReport | None:
        if type(report_id) is not int or not 0 < report_id <= 2**63 - 1:
            raise ValueError('invalid report number')
        row = self._db.execute(
            '''SELECT r.trial_id, r.forecast_time, r.phases, r.provenance, i.receipt_id
               FROM reports AS r JOIN issue_receipts AS i USING (report_id)
               WHERE r.report_id = ?''', (report_id,)
        ).fetchone()
        if row is None:
            return None
        trial_id, time, phases, provenance, receipt_id = row
        trial = TrialId(trial_id)
        return PublishedReport(
            report_id, trial, decode_rational(time), decode_phase_set(json.loads(phases)),
            decode_provenance(json.loads(provenance), trial), IssueReceipt(report_id, receipt_id),
        )
