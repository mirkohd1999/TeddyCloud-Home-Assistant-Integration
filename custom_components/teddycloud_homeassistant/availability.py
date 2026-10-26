"""Local receipt-time based availability; retained MQTT is not a heartbeat."""
import time


def timeout_minutes(value):
    try:
        return min(120, max(1, int(value)))
    except (TypeError, ValueError):
        return 5


class Availability:
    def __init__(self, minutes=5, clock=time.monotonic):
        self.timeout = timeout_minutes(minutes) * 60
        self.clock = clock
        self.last_message = None

    def received(self, retained=False):
        if not retained:
            self.last_message = self.clock()

    @property
    def online(self):
        return self.last_message is not None and self.clock() - self.last_message < self.timeout
