import re
from datetime import date
from sqlalchemy import Date

from .serializer import ColumnSerializer


class DateTimeSerializer(ColumnSerializer):
    """
    Serializer for DateTime objects
    """

    DATE_REGEX = '(?P<Y>\d{2,4})-(?P<m>\d{2})-(?P<d>\d{2})'

    DATE_RE = re.compile(DATE_REGEX)

    def dump(self, value):
        return value.isoformat()

    def load(self, serialized):
        match = self.DATE_RE.match(serialized)
        if not match:
            raise ValueError("Could not parse Date: '{}'".format(serialized))
        parts = match.groupdict()
        dt = date(int(parts['Y']), int(parts['m']), int(parts['d']))
        return dt


def is_date_field(col):
    """
    Check if a column is DateTime (or implements DateTime)

    :param Column col: the column object to be checked

    :rtype: bool
    """

    if hasattr(col.type, 'impl'):
        return type(col.type.impl) is Date
    else:
        return type(col.type) is Date
