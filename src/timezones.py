"""Provides implementations of datetime.tzinfo for the world's timezones.

UNIVERSAL: Represents the UTC timezone.
HAWAII: Represents the Hawaii-Aleutia timezone for locations that do not observe DST.
ALEUTIA: Represents the Hawaii-Aleutia timezone for locations that observe DST.
ALASKA: Represents the Alaskan timezone.
PACIFIC: Represents the Pacific timezone.
ARIZONA: Represents the Mountain timezone for locations that do not observe DST.
MOUNTAIN: Represents the Mountain timezone for locations that observe DST.
CENTRAL: Represents the Central timezone.
EASTERN: Represents the Eastern timezone.
LOCAL: References the local timezone.
"""

import datetime as _dt


class _FixedTimezone(_dt.tzinfo):
    # Represents a timezone with a fixed offset.

    def __init__(self, offset, name):
        self._offset = offset
        self._name = name

    def utcoffset(self, dt):
        return _dt.timedelta(hours=self._offset)

    def dst(self, dt):
        return _dt.timedelta(0)

    def tzname(self, dt):
        return self._name

    def __repr__(self):
        return self._name


class _DstTimezone(_dt.tzinfo):
    # Represents a timezone that observes daylight savings time.

    def __init__(self, std_offset, dst_on, std_on):
        self._offset = std_offset
        self._dst_name = dst_on[0]
        self._std_name = std_on[0]
        self._dst_on = dst_on[1:]
        self._dst_end = std_on[1:]

    @staticmethod
    def _find_date(year, month, week, day,  hour=0, minute=0):
        result = _dt.datetime(year, month, 7 * week, hour, minute)
        for i in range(6):
            if result.weekday() == day:
                return result
            result -= _dt.timedelta(days=1)

    def utcoffset(self, dt):
        return _dt.timedelta(hours=self._offset) + self.dst(dt)

    def dst(self, dt):
        if dt is None:
            return _dt.timedelta(hours=0)
        start = self._find_date(dt.year, *self._dst_on)
        end = self._find_date(dt.year, *self._dst_end)

        if start <= dt.replace(tzinfo=None) < end:
            return _dt.timedelta(hours=1)
        else:
            return _dt.timedelta(hours=0)

    def tzname(self, dt):
        if self.dst(dt):
            return self._dst_name
        else:
            return self._std_name

    def __repr__(self):
        return f'{self._dst_name}/{self._std_name}'


# Timezones Objects
UNIVERSAL = _FixedTimezone(0, 'UTC')
HAWAII = _FixedTimezone(-10, 'HAST')
ALEUTIA = _DstTimezone(-10, ('HADT', 3, 2, 6, 2), ('HAST', 11, 1, 6, 1))
ALASKA = _DstTimezone(-9, ('AKDT', 3, 2, 6, 2), ('AKST', 11, 1, 6, 1))
PACIFIC = _DstTimezone(-8, ('PDT', 3, 2, 6, 2), ('PST', 11, 1, 6, 1))
ARIZONA = _FixedTimezone(-7, 'MST')
MOUNTAIN = _DstTimezone(-7, ('MDT', 3, 2, 6, 2), ('MST', 11, 1, 6, 1))
CENTRAL = _DstTimezone(-6, ('CDT', 3, 2, 6, 2), ('CST', 11, 1, 6, 1))
EASTERN = _DstTimezone(-5, ('EDT', 3, 2, 6, 2), ('EST', 11, 1, 6, 1))

# Local Timezone
LOCAL = CENTRAL
