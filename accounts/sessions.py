from django.contrib.sessions.models import Session
from django.utils import timezone


def end_all_sessions(user):
    """Sign this member out on every phone and browser. Returns how many sessions were ended."""
    ended = 0
    wanted = str(user.pk)
    for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if session.get_decoded().get("_auth_user_id") == wanted:
            session.delete()
            ended += 1
    return ended
