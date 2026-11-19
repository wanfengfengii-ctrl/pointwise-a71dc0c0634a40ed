import json
import sqlite3

from phase.observations.intake import correct
from phase.reports.export import export_report, read
from tests.support import LabTest, point


class ReportTests(LabTest):
    def test_publish_rollback(self):
        self.register_trial()
        artifact = self.fixed('A', 'tick', 0, '1/4', '1/4')
        self.close_sources()
        old = self.predict([artifact], 2)
        before = self.report_rows()
        # The trigger inserts a violation whose check runs at COMMIT, after both writes.
        self.center.executescript('''
            CREATE TABLE allowed_commit_guard (key INTEGER PRIMARY KEY);
            CREATE TABLE deferred_commit_guard (
                key INTEGER REFERENCES allowed_commit_guard(key) DEFERRABLE INITIALLY DEFERRED
            );
            CREATE TRIGGER reject_report_commit AFTER INSERT ON issue_receipts
            BEGIN
                INSERT INTO deferred_commit_guard VALUES (17);
            END;
        ''')
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'FOREIGN KEY'):
            self.predict([artifact], 3)
        self.assertFalse(self.center.in_transaction)
        self.reopen_center()
        self.assertEqual(self.report_rows(), before)
        self.assertEqual(self.center.execute('SELECT COUNT(*) FROM deferred_commit_guard').fetchone(), (0,))
        self.assertEqual(read(self.reports, old.report_id), old)
        self.assertIsNone(read(self.reports, old.report_id + 1))
        self.center.execute('DROP TRIGGER reject_report_commit')
        retried = self.predict([artifact], 3)
        self.assertNotEqual(retried.report_id, old.report_id)
        self.assertEqual(retried.phases, (point('1/4'),))
        self.assertEqual(retried.time, 3)
        self.assertEqual(self.report_rows(), (
            before[0] + [(retried.report_id,)],
            before[1] + [(retried.report_id, retried.receipt.receipt_id)],
        ))

    def test_report_survives_new_observation(self):
        self.register_trial()
        old_revision = self.record('A', 'flash', 0, '1/8', '1/8')
        old_id = self.collect(self.package('A', old_revision))
        old = self.predict([old_id], 2)
        old_export = export_report(self.reports, old.report_id)
        newer = correct(self.registry, self.observations['A'], old_revision.ref.key,
                        old_revision.ref, 0, '1/4', '1/4')
        new_id = self.collect(self.package('A', newer))
        self.close_sources()
        new = self.predict([new_id], 3)
        self.reopen_center()
        self.assertEqual(read(self.reports, old.report_id), old)
        self.assertEqual(read(self.reports, new.report_id), new)
        self.assertEqual(old.phases, (point('1/8'),))
        self.assertEqual(new.phases, (point('1/4'),))
        self.assertEqual((old.provenance[0].artifact_id, old.provenance[0].revisions),
                         (old_id, (old_revision.ref,)))
        self.assertEqual((new.provenance[0].artifact_id, new.provenance[0].revisions),
                         (new_id, (newer.ref,)))
        self.assertNotEqual(old.receipt, new.receipt)
        self.assertEqual(export_report(self.reports, old.report_id), old_export)

    def test_export_stored_exact_snapshot(self):
        self.register_trial()
        artifact = self.fixed('A', 'wrap', 0, '3/4', '1/4')
        self.close_sources()
        report = self.predict([artifact], '5/2')
        self.reopen_center()
        data = json.loads(export_report(self.reports, report.report_id))
        self.assertEqual(data, {
            'report_id': report.report_id,
            'trial_id': 'trial-1',
            'time': '5/2',
            'phases': [['0', '1/4', True, True], ['3/4', '1', True, False]],
            'provenance': [{'artifact_id': artifact, 'station': 'A', 'source': 'east-desk',
                            'revisions': [['wrap', 1]]}],
            'receipt': {'report_id': report.report_id, 'receipt_id': 'R-000001'},
        })

    def test_unknown_report(self):
        self.register_trial()
        artifact = self.fixed('A', 'tick', 0, 0, 0)
        report = self.predict([artifact], 0)
        unknown = report.report_id + 100
        self.reopen_center()
        self.assertIsNone(read(self.reports, unknown))
        self.assertIsNone(export_report(self.reports, unknown))
        self.assertEqual(read(self.reports, report.report_id), report)
