"""Box activity deadlines with bounded, estimated playback protection."""
from datetime import datetime
import math
import time

PLAYBACK_BUFFER = 120


def timeout_minutes(value):
    try:
        return min(120, max(1, int(value)))
    except (TypeError, ValueError):
        return 5


def timestamp(value):
    """Accept timezone-aware ISO timestamps and Unix seconds; reject ambiguity."""
    try:
        if isinstance(value, str) and not value.strip().replace('.', '', 1).isdigit():
            parsed = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                return None
            value = parsed.timestamp()
        value = float(value)
        return value if math.isfinite(value) and value > 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


class Availability:
    def __init__(self, minutes=5, clock=time.monotonic, wall_clock=time.time):
        self.timeout = timeout_minutes(minutes) * 60
        self.clock = clock
        self.wall_clock = wall_clock
        self.last_message = None
        self.last_seen = None
        self._seen_at = None
        self.stopped_at = None
        self.playback_started = None
        self._pending_start = None
        self.duration = None

    def received(self, retained=False, last_seen=None):
        if retained:
            return
        self.last_message = self.clock()
        seen = timestamp(last_seen)
        # Do not let bad timestamps or repeated server snapshots extend life.
        if seen is not None and seen <= self.wall_clock() + 60:
            if self.last_seen is None or seen > self.last_seen:
                self.last_seen = seen
                self._seen_at = self.clock() - max(0, self.wall_clock() - seen)
        if (self.playback_started is None and self._pending_start is not None
                and self.clock() - self._pending_start < self.timeout
                and self.activity_remaining > 0):
            self.playback_started = self._pending_start

    @property
    def activity_remaining(self):
        source = self._seen_at if self._seen_at is not None else self.last_message
        deadlines = [v + self.timeout for v in (source, self.stopped_at) if v is not None]
        return max(0, max(deadlines) - self.clock()) if deadlines else 0

    def start_playback(self):
        # Retained/old snapshots must not create a new full-length playback window.
        self._pending_start = self.clock()
        if self.activity_remaining > 0:
            self.playback_started = self._pending_start

    def stop_playback(self, fresh=False):
        self.playback_started = None
        self._pending_start = None
        if fresh:
            self.stopped_at = self.clock()

    @property
    def playback_remaining(self):
        duration = self.duration
        if (self.playback_started is None or isinstance(duration, bool)
                or not isinstance(duration, (float, int)) or not 0 < duration <= 86400):
            return 0
        return max(0, self.playback_started + duration + PLAYBACK_BUFFER - self.clock())

    @property
    def remaining(self):
        return max(self.activity_remaining, self.playback_remaining)

    @property
    def online(self):
        return self.remaining > 0
