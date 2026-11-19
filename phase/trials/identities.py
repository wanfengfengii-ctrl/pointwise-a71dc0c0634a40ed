from typing import NewType


TrialId = NewType('TrialId', str)
GaugeId = NewType('GaugeId', str)
StationId = NewType('StationId', str)


def require_id(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f'{label} must be a nonempty identifier')
    if any(ord(character) < 32 for character in value):
        raise ValueError(f'{label} contains a control character')
    return value
