from contextlib import closing
import json

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

SOURCES = {"A": "east-desk", "B": "west-desk"}
# packages 中每项为 (站点, 钟差预算, 本件读数)。每条读数为 (观测号, 名义秒, 弧始, 弧末)。
CASES = {
    "same_station": {
        "times": (0, 4), "drift": ("1/4", "1/4"), "forecast_at": 0,
        "packages": [
            ("A", ("-1/2", "1/2"), [("zero", 1, 0, 0)]),
            ("A", ("-1/2", "1/2"), [("half", 2, "1/2", "1/2")]),
        ],
        "expected": [],
    },
    "separate_stations": {
        "times": (0, 4), "drift": ("1/4", "1/4"), "forecast_at": 0,
        "packages": [
            ("A", (0, 1), [("zero", 1, 0, 0)]),
            ("B", (0, 1), [("quarter", 1, "1/4", "1/4")]),
        ],
        "expected": [["3/4", "3/4", True, True]],
    },
    "lifted_tick": {
        "times": (0, 4), "drift": ("1/4", "1/4"), "forecast_at": 0,
        "packages": [("A", (1, 1), [("flash", 1, "3/8", "3/8")])],
        "expected": [["7/8", "7/8", True, True]],
    },
    "negative_drift": {
        "times": (0, 4), "drift": ("-1/4", "-1/4"), "forecast_at": 0,
        "packages": [("A", (0, 1), [("zero", 1, 0, 0)])],
        "expected": [["1/4", "1/2", True, True]],
    },
    "zero_drift": {
        "times": (0, 4), "drift": (0, 0), "forecast_at": 0,
        "packages": [("A", (0, 1), [("zero", 1, 0, 0)])],
        "expected": [["0", "0", True, True]],
    },
    "open_seam": {
        "times": (0, 4), "drift": (0, "1/4"), "forecast_at": 0,
        "packages": [("A", ("1/2", "1/2"), [("zero", 1, 0, 0)])],
        "expected": [["0", "0", True, True], ["5/8", "1", True, False]],
    },
    "time_clipped": {
        "times": (1, 2), "drift": ("1/4", "1/4"), "forecast_at": 1,
        "packages": [("A", (-1, 0), [("zero", 1, 0, 0)])],
        "expected": [["0", "0", True, True]],
    },
}


def record_case(case_id, registry, station_ledgers):
    """Use the original intake API to create explicit revision references."""
    case = CASES[case_id]
    trial = register(registry, case_id, "gauge-17", SOURCES, case["times"], case["drift"])
    selections = []
    for station, bounds, rows in case["packages"]:
        refs = [record_arc(registry, station_ledgers[station], trial, station, *row).ref
                for row in rows]
        selections.append((station, bounds, refs))
    return trial, selections


def show_v1_boundary():
    case_id = "lifted_tick"
    with closing(connect(":memory:")) as center:
        registry = TrialRegistry(center)
        catalog = AcceptedCatalog(center)
        reports = ReportLedger(center)
        with closing(connect(":memory:")) as station_db:
            observations = ObservationLedger(station_db)
            issues = StationLedger(station_db)
            trial, [(station, _, refs)] = record_case(case_id, registry, {"A": observations})
            package = issue(registry, observations, issues, trial, station, refs)
            lifted_upper = [str(upper.limit) for upper, _ in package.evidence.clauses[0].alternatives]
            artifact_id = accept(registry, catalog, encode_artifact(package), package.source)
        report = forecast(registry, catalog, reports, [artifact_id], CASES[case_id]["forecast_at"])
        phases = encode_phase_set(report.phases)
        if (lifted_upper != ["3/8"] or phases != [["1/8", "1/8", True, True]]
                or read(reports, report.report_id) != report):
            raise AssertionError(f"Unexpected V1 report: {lifted_upper!r}, {phases!r}")
        print(json.dumps({"case": case_id, "v1_lifted_upper": lifted_upper,
                          "v1_nominal_phases": phases}, sort_keys=True))


if __name__ == "__main__":
    show_v1_boundary()
