from fractions import Fraction

from phase.observations.intake import correct, record_arc
from phase.observations.revisions import ObservationKey, RevisionRef
from tests.support import LabTest, TRIAL


class ObservationTests(LabTest):
    def test_reject_out_of_range_phase(self):
        self.register_trial()
        good = self.record('A', 'good', 0, 0, '1/4')
        with self.assertRaisesRegex(ValueError, 'phase endpoint'):
            self.record('A', 'bad', 0, 0, 1)
        key = ObservationKey(TRIAL, 'A', 'bad')
        ledger = self.observations['A']
        self.assertIsNone(ledger.current_ref(key))
        self.assertIsNone(ledger.read_revision(RevisionRef(key, 1)))
        self.assertEqual(ledger.read_revision(good.ref), good)

    def test_domain_and_membership(self):
        for times, drift in [((-1, 4), (0, 0)), ((0, 5), (0, 0)), ((1, 0), (0, 0)),
                             ((0, 4), ('-1/3', 0)), ((0, 4), (0, '1/3')),
                             ((0, 4), ('1/4', 0)), ((0, 4), (0.0, 0))]:
            with self.subTest(times=times, drift=drift):
                with self.assertRaises(ValueError):
                    self.register_trial(drift, times)
        self.assertEqual(self.center.execute('SELECT COUNT(*) FROM trials').fetchone(), (0,))
        self.register_trial(times=(1, 3))
        local = self.observations['A']
        for trial, station, time in [(TRIAL, 'C', 1), ('unknown', 'A', 1), (TRIAL, 'A', 0)]:
            with self.subTest(trial=trial, station=station, time=time):
                with self.assertRaises(ValueError):
                    record_arc(self.registry, local, trial, station, 'unrecorded', time, 0, 0)
        self.assertEqual(self.station_dbs['A'].execute('SELECT COUNT(*) FROM observation_revisions').fetchone(), (0,))
        received = self.record('A', 'edge', 3, 0, 0)
        self.assertEqual(received.time, Fraction(3))
        self.assertTrue(received.arc.is_tick())

    def test_duplicate_intake_preserves_first_revision(self):
        self.register_trial()
        original = self.record('A', 'flash', 0, '3/4', '1/4')
        self.assertTrue(original.arc.crosses_zero())
        with self.assertRaisesRegex(ValueError, 'already recorded'):
            self.record('A', 'flash', 1, '1/8', '1/8')
        ledger = self.observations['A']
        self.assertEqual(ledger.current_ref(original.ref.key), original.ref)
        self.assertEqual(ledger.read_revision(original.ref), original)
        self.assertEqual(self.station_dbs['A'].execute('SELECT COUNT(*) FROM observation_revisions').fetchone(), (1,))

    def test_correction_keeps_old_revision(self):
        self.register_trial()
        ledger = self.observations['A']
        first = self.record('A', 'flash', 0, '1/8', '1/8')
        key = first.ref.key
        second = correct(self.registry, ledger, key, first.ref, 1, '1/4', '1/4')
        self.assertEqual(second.parent, first.ref)
        self.assertEqual((second.arc.start, second.arc.end, second.time), (Fraction(1, 4), Fraction(1, 4), 1))
        stored_old = ledger.read_revision(first.ref)
        self.assertEqual((stored_old.arc.start, stored_old.arc.end, stored_old.time), (Fraction(1, 8), Fraction(1, 8), 0))
        for parent in (first.ref, RevisionRef(key, 100)):
            with self.assertRaisesRegex(ValueError, 'parent revision'):
                correct(self.registry, ledger, key, parent, 2, '3/8', '3/8')
        with self.assertRaisesRegex(ValueError, 'phase endpoint'):
            correct(self.registry, ledger, key, second.ref, 2, '3/8', 1)
        self.assertEqual(ledger.current_ref(key), second.ref)
        self.assertEqual(ledger.read_revision(second.ref), second)
        self.assertIsNone(ledger.read_revision(RevisionRef(key, 3)))

    def test_initialize_again_preserves_registration_and_correction(self):
        self.register_trial(('-1/4', '1/4'))
        snapshot = self.registry.get_trial(TRIAL)
        old = self.record('A', 'flash', 0, '1/8', '1/8')
        new = correct(self.registry, self.observations['A'], old.ref.key, old.ref, 1, '1/4', '1/4')
        self.reopen_center()
        self.reopen_station('A')
        with self.assertRaisesRegex(ValueError, 'already registered'):
            self.register_trial()
        self.assertEqual(self.registry.get_trial(TRIAL), snapshot)
        local = self.observations['A']
        self.assertEqual(local.read_revision(old.ref), old)
        self.assertEqual(local.read_revision(new.ref), new)
        self.assertEqual(local.current_ref(old.ref.key), new.ref)
