from django import template
from django.utils.safestring import mark_safe
from datetime import datetime
from django.utils import timezone

register = template.Library()


def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc.
    Ref: https://stackoverflow.com/questions/1551382/user-friendly-time-format-in-python
    """
    # Ref: https://stackoverflow.com/questions/33248809/python-django-timezone-is-not-working-properly
    now = timezone.now()  # datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = 0
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff // 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff // 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff // 7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff // 30) + " months ago"
    return str(day_diff // 365) + " years ago"


@register.simple_tag
def get_time_ago(time):
    # Ref: https://stackoverflow.com/questions/796008/cant-subtract-offset-naive-and-offset-aware-datetimes
    naive_time = time  # time.replace(tzinfo=None)
    return pretty_date(naive_time)
