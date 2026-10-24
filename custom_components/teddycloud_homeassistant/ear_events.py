"""Decode TeddyCloud ear-button MQTT event payloads without HA dependencies."""
import json

EAR_EVENTS = frozenset({"pressed", "double-pressed", "triple-pressed"})


def parse_ear_event(payload):
    """Return a documented ear event or None for malformed/unknown messages.

    TeddyCloud publishes JSON such as {"event_type": "pressed"} on VolUp/VolDown.
    Never interpret a volume level or an arbitrary payload as a button press.
    """
    if isinstance(payload, memoryview):
        payload = payload.tobytes()
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    event_type = value.get("event_type")
    return event_type if isinstance(event_type, str) and event_type in EAR_EVENTS else None
