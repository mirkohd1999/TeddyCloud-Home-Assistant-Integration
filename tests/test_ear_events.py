"""Tests for TeddyCloud physical ear press payloads (no HA runtime required)."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "custom_components" / "teddycloud_homeassistant" / "ear_events.py"
spec = importlib.util.spec_from_file_location("ear_events", MODULE)
ear_events = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ear_events)


class EarEventsTest(unittest.TestCase):
    def test_single_double_and_triple_press(self):
        for event in ("pressed", "double-pressed", "triple-pressed"):
            with self.subTest(event=event):
                self.assertEqual(ear_events.parse_ear_event(('{"event_type":"' + event + '"}').encode()), event)

    def test_additional_json_fields(self):
        self.assertEqual(
            ear_events.parse_ear_event('{"event_type": "pressed", "other": "ignored"}'),
            "pressed",
        )

    def test_reject_unrelated_or_malformed_events(self):
        payloads = [
            None, "", b"", b"\xff", "pressed", "1", "true", "null",
            "[]", "{}", '{"event_type":123}', '{"event_type":null}',
            '{"event_type":"released"}', '{"event_type":"PRESS"}',
            '{"event_type":"pressed"', '{"foo":"pressed"}',
        ]
        for raw in payloads:
            with self.subTest(raw=raw):
                self.assertIsNone(ear_events.parse_ear_event(raw))

    def test_memoryview_payload(self):
        self.assertEqual(
            ear_events.parse_ear_event(memoryview(b'{"event_type":"pressed"}')),
            "pressed",
        )


if __name__ == "__main__":
    unittest.main()
