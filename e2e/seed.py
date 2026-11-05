"""Seeds the e2e database. Run with:  python manage.py shell < e2e/seed.py   (fake people only)."""
import datetime
import random

from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.utils import timezone

from accounts.models import ParentLink, User
from learn import services
from learn.models import Attempt, Goal, Question, ScoreEstimate

PW = "Correct-horse-battery-9"
HASH = make_password(PW)
call_command("seed_content", verbosity=0)
today = timezone.localdate()


def make(username, name, role="student", status="approved", **extra):
    u = User(username=username, display_name=name, role=role, approval_status=status, password=HASH, **extra)
    u.approved_at = timezone.now() if status == "approved" else None
    u.save()
    return u


def goal(u):
    Goal.objects.create(user=u, current_score=1000, target_score=1300, target_school="State U",
                        test_date=today + datetime.timedelta(days=60), minutes_per_day=30)


boss = make("boss", "Boss", is_staff=True, is_superuser=True, ad_free=True)
sam = make("sam", "Sam")
goal(sam)
random.seed(5)
qs = list(Question.objects.all())
for back in range(13, -1, -1):
    for _ in range(random.choice([0, 6, 9, 12])):
        q = random.choice(qs)
        a = services.record_attempt(sam, q, q.correct_answer.split("|")[0] if random.random() < .7 else "zzz", seconds=30)
        Attempt.objects.filter(pk=a.pk).update(created_at=timezone.now() - datetime.timedelta(days=back))
for i, v in enumerate([1000, 1020, 1050, 1080, 1100]):
    ScoreEstimate.objects.create(user=sam, on_date=today - datetime.timedelta(days=(4 - i) * 7), score=v)
dana = make("dana", "Dana", role="parent")
ParentLink.objects.create(parent=dana, child=sam)
make("lonely", "Lonely", role="parent")  # a parent with no linked child
make("waiting", "Waiting", status="pending")
make("rejected", "Rejected", status="rejected")
for i in range(70):
    goal(make(f"k{i:02d}", f"Kid {i:02d}"))
for i in range(25):
    make(f"n{i:02d}", f"New {i:02d}")  # approved, no goal yet
print("seeded")
