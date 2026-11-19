from collections.abc import Mapping
from dataclasses import dataclass
import sqlite3

from phase.storage import initialize, write_transaction
from phase.trials.domain import TrialDomain, make_trial_domain
from phase.trials.identities import GaugeId, StationId, TrialId, require_id
from phase.trials.rational import decode_rational, encode_rational
from phase.trials.stations import StationSource


_SCHEMA = '''
CREATE TABLE IF NOT EXISTS trials (
    trial_id TEXT PRIMARY KEY,
    gauge_id TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    drift_low TEXT NOT NULL,
    drift_high TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trial_stations (
    trial_id TEXT NOT NULL REFERENCES trials(trial_id),
    station_id TEXT NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (trial_id, station_id)
);
'''


@dataclass(frozen=True)
class RegisteredTrial:
    trial_id: TrialId
    gauge_id: GaugeId
    domain: TrialDomain
    stations: tuple[StationSource, ...]


class TrialRegistry:
    def __init__(self, connection: sqlite3.Connection):
        self._db = connection
        initialize(connection, _SCHEMA)

    def _insert(self, trial: RegisteredTrial) -> None:
        domain = trial.domain
        encoded_domain = tuple(map(encode_rational, (
            domain.start, domain.end, domain.drift_low, domain.drift_high,
        )))
        with write_transaction(self._db):
            existing = self._db.execute(
                'SELECT 1 FROM trials WHERE trial_id = ?', (trial.trial_id,)
            ).fetchone()
            if existing is not None:
                raise ValueError('trial number is already registered')
            self._db.execute(
                'INSERT INTO trials VALUES (?, ?, ?, ?, ?, ?)',
                (trial.trial_id, trial.gauge_id, *encoded_domain),
            )
            self._db.executemany(
                'INSERT INTO trial_stations VALUES (?, ?, ?)',
                [(trial.trial_id, entry.station, entry.source) for entry in trial.stations],
            )

    def get_trial(self, trial_id: str) -> RegisteredTrial:
        require_id(trial_id, 'trial')
        row = self._db.execute(
            '''SELECT gauge_id, start_time, end_time, drift_low, drift_high
               FROM trials WHERE trial_id = ?''', (trial_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f'unknown trial {trial_id!r}')
        gauge, start, end, low, high = row
        domain = make_trial_domain(
            (decode_rational(start), decode_rational(end)),
            (decode_rational(low), decode_rational(high)),
        )
        stations = self._db.execute(
            '''SELECT station_id, source FROM trial_stations
               WHERE trial_id = ? ORDER BY station_id''', (trial_id,)
        )
        return RegisteredTrial(
            TrialId(trial_id), GaugeId(gauge), domain,
            tuple(StationSource(StationId(station), source) for station, source in stations),
        )


def register(
    registry: TrialRegistry, trial_id: str, gauge_id: str,
    stations: Mapping[str, str], time_bounds, drift_bounds,
) -> TrialId:
    trial_key = TrialId(require_id(trial_id, 'trial'))
    gauge_key = GaugeId(require_id(gauge_id, 'gauge'))
    domain = make_trial_domain(time_bounds, drift_bounds)
    if not isinstance(stations, Mapping) or not stations:
        raise ValueError('at least one station must be registered')
    entries = [StationSource(StationId(station), source) for station, source in stations.items()]
    entries.sort(key=lambda entry: entry.station)
    registry._insert(RegisteredTrial(trial_key, gauge_key, domain, tuple(entries)))
    return trial_key
