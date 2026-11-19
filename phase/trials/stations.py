from dataclasses import dataclass
from typing import Iterable

from phase.trials.identities import StationId, require_id


@dataclass(frozen=True)
class StationSource:
    station: StationId
    source: str

    def __post_init__(self) -> None:
        require_id(self.station, 'station')
        require_id(self.source, 'station source')


def require_trial_station(stations: Iterable[StationSource], station: str) -> StationSource:
    require_id(station, 'station')
    for entry in stations:
        if station == entry.station:
            return entry
    raise ValueError(f'station {station!r} is outside the trial')


def verify_station_source(
    stations: Iterable[StationSource], declared: StationSource, submitted: StationSource
) -> StationSource:
    registered = require_trial_station(stations, declared.station)
    if registered != declared or registered != submitted:
        raise ValueError('station source does not match the trial registration')
    return registered
