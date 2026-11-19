import json

from phase.analysis.phase_set import encode_phase_set
from phase.reports.ledger import PublishedReport, ReportLedger
from phase.reports.provenance import encode_provenance
from phase.trials.rational import encode_rational


def read(ledger: ReportLedger, report_id: int) -> PublishedReport | None:
    return ledger.load_report(report_id)


def export_report(ledger: ReportLedger, report_id: int) -> str | None:
    report = read(ledger, report_id)
    if report is None:
        return None
    return json.dumps({
        'report_id': report.report_id,
        'trial_id': report.trial_id,
        'time': encode_rational(report.time),
        'phases': encode_phase_set(report.phases),
        'provenance': encode_provenance(report.provenance),
        'receipt': {'report_id': report.receipt.report_id, 'receipt_id': report.receipt.receipt_id},
    }, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
