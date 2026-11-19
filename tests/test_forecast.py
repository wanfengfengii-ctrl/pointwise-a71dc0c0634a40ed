from fractions import Fraction

from phase.reports.export import read
from tests.support import LabTest, interval, point


class ForecastTests(LabTest):
    def test_ordinary_offline_forecast(self):
        self.register_trial()
        east = self.fixed('A', 'east-flash', 0, '1/8', '3/8')
        west = self.fixed('B', 'west-flash', 0, '1/4', '1/2')
        self.close_sources()
        self.reopen_center()
        report = self.predict([west, east], 2)
        self.assertEqual(report.phases, (interval('1/4', '3/8'),))
        self.assertEqual(report.time, Fraction(2))
        self.assertEqual([item.artifact_id for item in report.provenance], sorted([east, west]))
        self.assertEqual({(p.source.station, p.source.source) for p in report.provenance},
                         {('A', 'east-desk'), ('B', 'west-desk')})
        self.assertEqual(read(self.reports, report.report_id), report)
        reordered = self.predict([east, west], 2)
        self.assertEqual(reordered.phases, report.phases)
        self.assertEqual(reordered.provenance, report.provenance)

    def test_wrapped_station_and_exact_tick(self):
        self.register_trial((0, '1/4'))
        east = self.fixed('A', 'wrap', 0, '3/4', '1/4')
        west = self.fixed('B', 'zero-tick', 1, 0, 0)
        self.close_sources()
        self.reopen_center()
        report = self.predict([east, west], 2)
        accepts_half = any(piece.contains(Fraction(1, 2)) for piece in report.phases)
        self.assertEqual(
            (report.phases, accepts_half), ((interval(0, '1/4'),), False),
            f'PHASE_FORECAST_MISMATCH actual={report.phases!r} accepts_half={accepts_half}',
        )
        self.assertEqual(read(self.reports, report.report_id), report)

    def test_complete_evidence_preserves_correlation(self):
        self.register_trial((0, '1/4'))
        # The initial arc avoids the seam. The second reading forces p+d=1.
        east = self.fixed('A', 'high-arc', 0, '3/4', '7/8')
        west = self.fixed('B', 'zero-tick', 1, 0, 0)
        self.close_sources()
        self.assertEqual(self.predict([east, west], 2).phases, (interval('1/8', '1/4'),))

    def test_seam_endpoints_after_negative_rotation(self):
        self.register_trial(('-1/4', '-1/4'))
        east = self.fixed('A', 'flash', 0, 0, '1/4')
        self.close_sources()
        self.assertEqual(self.predict([east], 1).phases,
                         (point(0), interval('3/4', 1, True, False)))

    def test_open_endpoint_coming_from_excluded_initial_phase(self):
        self.register_trial((0, '1/4'))
        west = self.fixed('B', 'zero-tick', 1, 0, 0)
        self.close_sources()
        self.assertEqual(self.predict([west], 0).phases, (point(0), interval('3/4', 1, True, False)))
        self.assertEqual(self.predict([west], 2).phases, (interval(0, '1/4'),))

    def test_separated_points_survive_publication(self):
        self.register_trial(('-1/4', '1/4'))
        east = self.fixed('A', 'tick0', 0, '1/4', '1/4')
        west = self.fixed('B', 'tick4', 4, '1/4', '1/4')
        self.close_sources()
        report = self.predict([east, west], 2)
        self.assertEqual(report.phases, (point('1/4'), point('3/4')))
        self.assertEqual(read(self.reports, report.report_id), report)

    def test_incompatible_ticks(self):
        self.register_trial(('-1/4', '1/4'))
        zero = self.fixed('A', 'tick', 1, 0, 0)
        half = self.fixed('B', 'tick', 1, '1/2', '1/2')
        self.close_sources()
        report = self.predict([zero, half], 2)
        self.assertEqual(report.phases, ())
        self.assertEqual([entry.artifact_id for entry in report.provenance], sorted([zero, half]))
        self.assertEqual(read(self.reports, report.report_id), report)

    def test_compatible_ticks_keep_single_point(self):
        self.register_trial((0, 0))
        first = self.fixed('A', 'tick', 0, '3/8', '3/8')
        second = self.fixed('B', 'tick', 1, '3/8', '3/8')
        self.close_sources()
        self.assertEqual(self.predict([first, second], 4).phases, (point('3/8'),))

    def test_request_bounds(self):
        self.register_trial(times=(1, 3))
        observations = [self.record('A', f'flash-{index}', 1, 0, 0) for index in range(6)]
        six = self.collect(self.package('A', *observations))
        seventh = self.fixed('B', 'extra', 2, 0, 0)
        self.close_sources()
        for ids, time in [([six, seventh], 2), ([six], 4), ([six], 0), ([six], 2.0),
                          ([], 2), ([six, six], 2), (['missing'], 2)]:
            with self.subTest(ids=ids, time=time):
                with self.assertRaises(ValueError):
                    self.predict(ids, time)
        self.assertEqual(self.report_rows(), ([], []))
        self.assertEqual(self.predict([six], 3).phases, (point(0),))

    def test_reject_cross_trial_forecast(self):
        self.register_trial()
        self.register_trial(trial='trial-2')
        first = self.fixed('A', 'first', 0, 0, 0)
        second = self.fixed('B', 'second', 0, 0, 0, 'trial-2')
        self.close_sources()
        old = self.predict([first], 0)
        before = self.report_rows()
        with self.assertRaisesRegex(ValueError, 'mix trials'):
            self.predict([first, second], 0)
        self.assertEqual(self.report_rows(), before)
        self.assertEqual(read(self.reports, old.report_id), old)
