from contextlib import ExitStack, closing
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from phase.analysis.catalog import AcceptedCatalog
from phase.analysis.forecast import forecast
from phase.analysis.intake import accept
from phase.analysis.phase_set import encode_phase_set
from phase.observations.intake import record_arc
from phase.observations.ledger import ObservationLedger
from phase.reports.export import read
from phase.reports.ledger import ReportLedger
from phase.station.artifact import encode_artifact
from phase.station.issue import issue
from phase.station.ledger import StationLedger
from phase.storage import connect
from phase.trials.registry import TrialRegistry, register
from phase.trials.stations import StationSource


SOURCES = {'east': 'east-desk', 'west': 'west-desk'}


def run_case(directory: Path, case: dict) -> None:
    directory.mkdir()
    data = case['input']
    center_path = directory / 'center.sqlite'
    with closing(connect(center_path)) as center:
        registry = TrialRegistry(center)
        catalog = AcceptedCatalog(center)
        reports = ReportLedger(center)
        trial = register(registry, case['case_id'], 'gauge-17', SOURCES, (0, 4), data['drift'])
        selected = []
        with ExitStack() as station_connections:
            for station, source in SOURCES.items():
                local = station_connections.enter_context(closing(connect(directory / f'{station}.sqlite')))
                observations = ObservationLedger(local)
                issues = StationLedger(local)
                revision = record_arc(registry, observations, trial, station, 'flash', *data[station])
                package = issue(registry, observations, issues, trial, station, [revision.ref])
                selected.append(accept(registry, catalog, encode_artifact(package), StationSource(station, source)))
        report = forecast(registry, catalog, reports, selected, data['forecast_at'])
        actual = encode_phase_set(report.phases)
        if actual != case['expected']:
            raise AssertionError(f'PHASE_FORECAST_MISMATCH {case["case_id"]} expected {case["expected"]}, got {actual}')

    with closing(connect(center_path)) as reopened:
        stored = read(ReportLedger(reopened), report.report_id)
        if stored != report:
            raise AssertionError('reopened report differs from the issued snapshot')
        expected_downstream = {
            'phases': case['expected'], 'artifacts': sorted(selected), 'receipt': 'R-000001',
        }
        actual_downstream = {
            'phases': encode_phase_set(stored.phases),
            'artifacts': [entry.artifact_id for entry in stored.provenance],
            'receipt': stored.receipt.receipt_id,
        }
        if actual_downstream != expected_downstream:
            raise AssertionError(f'reopened report expected {expected_downstream}, got {actual_downstream}')

    print('POINTWISE_SCENARIO ' + json.dumps({
        'case_id': case['case_id'], 'input': data, 'expected': case['expected'], 'actual': actual,
        'downstream_expected': expected_downstream, 'downstream_actual': actual_downstream,
        'code_paths': ['phase/station/issue.py', 'phase/station/calibration.py',
                       'phase/analysis/intake.py', 'phase/analysis/constraints.py',
                       'phase/analysis/forecast.py', 'phase/reports/ledger.py'],
        'oracle': case['oracle'],
    }, ensure_ascii=False, sort_keys=True))


def main() -> None:
    cases = json.loads(Path(__file__).with_name('example.json').read_text(encoding='utf-8'))
    with TemporaryDirectory(prefix='strobe-demo-') as name:
        for case in cases:
            run_case(Path(name) / case['case_id'], case)


if __name__ == '__main__':
    main()
