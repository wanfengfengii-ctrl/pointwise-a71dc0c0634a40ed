from phase.analysis.phase_set import PhaseInterval, normalize_phase_set
from phase.analysis.selection import ForecastSelection
from phase.reports.ledger import PublishedReport, ReportLedger
from phase.reports.provenance import capture_provenance


def publish_report(
    ledger: ReportLedger, selection: ForecastSelection, phases: tuple[PhaseInterval, ...],
) -> PublishedReport:
    if phases != normalize_phase_set(phases):
        raise ValueError('report needs a canonical phase set')
    provenance = capture_provenance(selection.trial, selection.artifacts)
    return ledger.commit_report(selection.trial.trial_id, selection.time, phases, provenance)
