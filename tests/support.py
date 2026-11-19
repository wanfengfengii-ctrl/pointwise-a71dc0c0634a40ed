from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from phase.analysis.catalog import AcceptedCatalog
from phase.analysis.forecast import forecast
from phase.analysis.intake import accept
from phase.analysis.phase_set import PhaseInterval
from phase.observations.intake import record_arc
from phase.observations.ledger import ObservationLedger
from phase.reports.ledger import ReportLedger
from phase.station.artifact import encode_artifact
from phase.station.issue import issue
from phase.station.ledger import StationLedger
from phase.storage import connect
from phase.trials.registry import TrialRegistry, register


SOURCES = {'A': 'east-desk', 'B': 'west-desk'}
TRIAL = 'trial-1'


def interval(low, high, lower_closed=True, upper_closed=True):
    return PhaseInterval(Fraction(low), Fraction(high), lower_closed, upper_closed)


def point(value):
    return interval(value, value)


class LabTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory(prefix='strobe-tests-')
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.center = None
        self.station_dbs = {}
        self.observations = {}
        self.issues = {}
        self.addCleanup(self.close)
        self.reopen_center()
        for station in SOURCES:
            self.reopen_station(station)

    def reopen_center(self):
        if self.center is not None:
            self.center.close()
        self.center = connect(self.root / 'center.sqlite')
        self.registry = TrialRegistry(self.center)
        self.catalog = AcceptedCatalog(self.center)
        self.reports = ReportLedger(self.center)

    def reopen_station(self, station):
        if station in self.station_dbs:
            self.station_dbs[station].close()
        db = connect(self.root / f'{station}.sqlite')
        self.station_dbs[station] = db
        self.observations[station] = ObservationLedger(db)
        self.issues[station] = StationLedger(db)

    def close_sources(self):
        for connection in self.station_dbs.values():
            connection.close()
        self.station_dbs.clear()

    def close(self):
        self.close_sources()
        if self.center is not None:
            self.center.close()

    def register_trial(self, drift=(0, 0), times=(0, 4), trial=TRIAL):
        return register(self.registry, trial, 'gauge-17', SOURCES, times, drift)

    def record(self, station, name, time, low, high, trial=TRIAL):
        return record_arc(self.registry, self.observations[station], trial, station, name, time, low, high)

    def package(self, station, *revisions, trial=TRIAL):
        return issue(self.registry, self.observations[station], self.issues[station],
                     trial, station, [revision.ref for revision in revisions])

    def collect(self, package):
        return accept(self.registry, self.catalog, encode_artifact(package), package.source)

    def fixed(self, station, name, time, low, high, trial=TRIAL):
        revision = self.record(station, name, time, low, high, trial)
        return self.collect(self.package(station, revision, trial=trial))

    def predict(self, ids, time):
        return forecast(self.registry, self.catalog, self.reports, ids, time)

    def report_rows(self):
        reports = self.center.execute('SELECT report_id FROM reports ORDER BY report_id').fetchall()
        receipts = self.center.execute('SELECT report_id, receipt_id FROM issue_receipts ORDER BY report_id').fetchall()
        return reports, receipts
