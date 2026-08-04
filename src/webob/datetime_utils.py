from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone, tzinfo
from email.utils import formatdate, mktime_tz, parsedate_tz
import time

from webob.util import text_

__all__ = [
    "UTC",
    "timedelta_to_seconds",
    "year",
    "month",
    "week",
    "day",
    "hour",
    "minute",
    "second",
    "parse_date",
    "serialize_date",
    "parse_date_delta",
    "serialize_date_delta",
    "utcnow",
]


def utcnow() -> datetime:
    """
    replacement of deprecated datetime.datetime.utcnow
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Hook point for unit tests. This is UTC based, not local: the values derived
# from it are serialized as GMT, so adding a delta to a local "now" would put
# the result out by the machine's UTC offset. See
# https://github.com/Pylons/webob/issues/430
_now = utcnow


class _UTC(tzinfo):
    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)

    def utcoffset(self, dt: datetime | None) -> timedelta:
        return timedelta(0)

    def tzname(self, dt: datetime | None) -> str:
        return "UTC"

    def __repr__(self) -> str:
        return "UTC"


UTC: _UTC = _UTC()


def timedelta_to_seconds(td: timedelta) -> int:
    """
    Converts a timedelta instance to seconds.
    """

    return td.seconds + (td.days * 24 * 60 * 60)


day: timedelta = timedelta(days=1)
week: timedelta = timedelta(weeks=1)
hour: timedelta = timedelta(hours=1)
minute: timedelta = timedelta(minutes=1)
second: timedelta = timedelta(seconds=1)
# Estimate, I know; good enough for expirations
month: timedelta = timedelta(days=30)
year: timedelta = timedelta(days=365)


def parse_date(value: str | bytes | None) -> datetime | None:
    if not value:
        return None
    try:
        if not isinstance(value, str):
            value = str(value, "latin-1")
    except Exception:
        return None
    t = parsedate_tz(value)

    if t is None:
        # Could not parse

        return None

    tt = mktime_tz(t)

    return datetime.fromtimestamp(tt, UTC)


def serialize_date(
    dt: (
        datetime
        | date
        | timedelta
        | time._TimeTuple
        | time.struct_time
        | float
        | str
        | bytes
    ),
) -> str:
    if isinstance(dt, (bytes, str)):
        return text_(dt)

    if isinstance(dt, timedelta):
        # The result is serialized as GMT (``usegmt=True`` below) via
        # ``calendar.timegm``, which reads the time tuple as UTC, so the "now"
        # the delta is added to must be UTC too.
        dt = _now() + dt

    if isinstance(dt, (datetime, date)):
        dt = dt.timetuple()

    if isinstance(dt, (tuple, time.struct_time)):
        dt = calendar.timegm(dt)

    if not (isinstance(dt, float) or isinstance(dt, int)):
        raise ValueError(
            "You must pass in a datetime, date, time tuple, or integer object, "
            "not %r" % dt
        )

    return formatdate(dt, usegmt=True)


def parse_date_delta(value: str | bytes | None) -> datetime | None:
    """
    like parse_date, but also handle delta seconds
    """

    if not value:
        return None
    try:
        int_value = int(value)
    except ValueError:
        return parse_date(value)
    else:
        return _now() + timedelta(seconds=int_value)


def serialize_date_delta(
    value: (
        datetime
        | date
        | timedelta
        | time._TimeTuple
        | time.struct_time
        | float
        | str
        | bytes
    ),
) -> str:
    if isinstance(value, (float, int)):
        return str(int(value))
    else:
        return serialize_date(value)
