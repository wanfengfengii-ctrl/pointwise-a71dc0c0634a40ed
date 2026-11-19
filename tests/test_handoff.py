from dataclasses import replace
import json

from phase.analysis.intake import accept
from phase.observations.intake import correct
from phase.observations.revisions import RevisionRef
from phase.station.artifact import encode_artifact
from phase.station.issue import issue
from phase.trials.stations import StationSource
from tests.support import LabTest, TRIAL, interval, point


class HandoffTests(LabTest):
    def test_reject_conflicting_package(self):
        self.register_trial()
        first = self.package('A', self.record('A', 'first', 0, '1/8', '1/8'))
        second = self.package('A', self.record('A', 'second', 0, '1/4', '1/4'))
        fixed_id = self.collect(first)
        conflicting = replace(second, artifact_id=fixed_id)
        with self.assertRaisesRegex(ValueError, 'different content'):
            self.collect(conflicting)
        self.close_sources()
        self.reopen_center()
        self.assertEqual(self.catalog.load(fixed_id).artifact, first)
        self.assertEqual(self.predict([fixed_id], 2).phases, (point('1/8'),))

    def test_repeat_intake_preserves_fixed_source(self):
        self.register_trial()
        original = self.package('A', self.record('A', 'flash', 0, '1/8', '1/8'))
        package_id = self.collect(original)
        self.reopen_center()
        text = json.dumps(json.loads(encode_artifact(original)), indent=2)
        self.assertEqual(accept(self.registry, self.catalog, text, original.source), package_id)
        self.assertEqual(self.center.execute('SELECT COUNT(*) FROM accepted_artifacts').fetchone(), (1,))
        self.assertEqual(self.catalog.load(package_id).source, original.source)

    def test_registered_source_binding(self):
        self.register_trial()
        original = self.package('A', self.record('A', 'flash', 0, 0, 0))
        wrong = StationSource('B', 'west-desk')
        with self.assertRaisesRegex(ValueError, 'source'):
            accept(self.registry, self.catalog, encode_artifact(original), wrong)
        forged = replace(original, source=StationSource('A', 'west-desk'))
        with self.assertRaisesRegex(ValueError, 'source'):
            self.collect(forged)
        self.assertIsNone(self.catalog.load(original.artifact_id))
        self.assertEqual(self.collect(original), original.artifact_id)

    def test_explicit_revision_after_correction(self):
        self.register_trial()
        old = self.record('A', 'flash', 0, '1/8', '1/8')
        current = correct(self.registry, self.observations['A'], old.ref.key, old.ref, 0, '1/4', '1/4')
        old_package = self.package('A', old)
        new_package = self.package('A', current)
        self.assertEqual(old_package.revisions, (old.ref,))
        self.assertEqual(new_package.revisions, (current.ref,))
        self.reopen_station('A')
        self.assertEqual(self.issues['A'].read_artifact(old_package.artifact_id), old_package)
        self.assertEqual(self.package('A', old), old_package)
        ids = self.collect(old_package), self.collect(new_package)
        self.close_sources()
        self.assertEqual(self.predict([ids[0]], 2).phases, (point('1/8'),))
        self.assertEqual(self.predict([ids[1]], 2).phases, (point('1/4'),))

    def test_invalid_selection_leaves_no_issue(self):
        self.register_trial()
        self.register_trial(trial='another-trial')
        local = self.record('A', 'flash', 0, 0, 0)
        other_site = self.record('B', 'flash', 0, 0, 0)
        other_trial = self.record('A', 'flash', 0, 0, 0, 'another-trial')
        missing = RevisionRef(local.ref.key, 99)
        for refs in [[], [local.ref, local.ref], [other_site.ref], [other_trial.ref], [missing]]:
            with self.subTest(refs=refs):
                with self.assertRaises(ValueError):
                    issue(self.registry, self.observations['A'], self.issues['A'], TRIAL, 'A', refs)
        self.assertEqual(self.station_dbs['A'].execute('SELECT COUNT(*) FROM station_issues').fetchone(), (0,))

    def test_offline_wrapped_branches(self):
        self.register_trial()
        artifact = self.fixed('A', 'wrap', 0, '3/4', '1/4')
        self.close_sources()
        self.assertEqual(self.predict([artifact], 0).phases, (
            interval('0', '1/4'), interval('3/4', '1', True, False),
        ))

    def test_exact_tick_evidence_offline(self):
        self.register_trial(('-1/4', '1/4'))
        artifact = self.fixed('B', 'tick', 1, 0, 0)
        self.close_sources()
        self.assertEqual(self.predict([artifact], 1).phases, (point(0),))

    def test_malformed_package_never_becomes_selectable(self):
        self.register_trial()
        artifact = self.package('A', self.record('A', 'first', 0, '1/8', '1/8'))
        payload = json.loads(encode_artifact(artifact))
        del payload['evidence']
        with self.assertRaises(ValueError):
            accept(self.registry, self.catalog, json.dumps(payload), artifact.source)
        self.assertIsNone(self.catalog.load(artifact.artifact_id))
