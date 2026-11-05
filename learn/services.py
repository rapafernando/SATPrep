"""The learning logic: planning, picking questions, grading, and the score estimate.

All of this is deliberately simple and explained in comments so it can be tuned later.
The score estimate in particular is a PLACEHOLDER model, not a calibrated SAT predictor.
"""
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from fractions import Fraction

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from .models import Attempt, Goal, PracticeSession, Question, ScoreEstimate, Skill, SkillProgress

MINUTES_PER_QUESTION = 1.5  # used to turn "minutes per day" into a question goal
MIN_DAILY_QUESTIONS, MAX_DAILY_QUESTIONS = 5, 60
SKILL_SESSION_LENGTH = 8
DEFAULT_MASTERY = 0.5  # same as SkillProgress.mastery default, for skills not tried yet
MASTERY_STEP = 0.25  # how fast the running average moves toward each new result
ESTIMATE_PRIOR_WEIGHT = 50  # attempts before the estimate trusts practice more than self-report


# ---------------------------------------------------------------- planning

@dataclass
class Plan:
    days_left: int
    daily_questions: int
    gain_needed: int
    weekly_gain_needed: float
    total_questions: int
    note: str


def plan_for(goal, today=None):
    today = today or timezone.localdate()
    days_left = (goal.test_date - today).days
    daily = max(MIN_DAILY_QUESTIONS, min(MAX_DAILY_QUESTIONS, round(goal.minutes_per_day / MINUTES_PER_QUESTION)))
    gain = goal.target_score - goal.current_score
    weeks = max(days_left / 7, 1)
    weekly = max(gain, 0) / weeks
    if days_left < 0:
        note = "Your test date has passed. Update your goal with the next date."
    elif gain <= 0:
        note = "You are already at your target. Keep practicing to stay sharp."
    elif weekly > 40:
        note = "That is an ambitious pace. Consider a later test date or more minutes per day."
    elif weekly > 20:
        note = "A challenging but realistic pace if you practice every day."
    else:
        note = "A comfortable pace. Consistency matters more than long sessions."
    return Plan(
        days_left=days_left,
        daily_questions=daily,
        gain_needed=gain,
        weekly_gain_needed=round(weekly, 1),
        total_questions=daily * max(days_left, 0),
        note=note,
    )


# ---------------------------------------------------------------- grading

def _to_fraction(text):
    text = text.strip().replace(",", "").replace(" ", "")
    if not text:
        raise ValueError("empty")
    if text.endswith("%"):
        text = text[:-1]
    return Fraction(text)


def grade(question, answer):
    answer = (answer or "").strip()
    if question.answer_type == Question.AnswerType.CHOICE:
        return answer.upper() == question.correct_answer.strip().upper()
    try:
        given = _to_fraction(answer)
    except (ValueError, ZeroDivisionError):
        return False
    for option in question.correct_answer.split("|"):
        try:
            if given == _to_fraction(option):
                return True
        except (ValueError, ZeroDivisionError):
            continue
    return False


# ---------------------------------------------------------------- picking questions

def pick_questions(user, n, skill=None, rng=None):
    """Mix skills, favouring ones the member knows least; unseen and long-ago questions first."""
    rng = rng or random.Random()
    queryset = Question.objects.filter(is_active=True, skill__is_active=True)
    if skill is not None:
        queryset = queryset.filter(skill=skill)
    by_skill = defaultdict(list)
    for question in queryset:
        by_skill[question.skill_id].append(question)
    if not by_skill:
        return []

    mastery = {p.skill_id: p.mastery for p in SkillProgress.objects.filter(user=user)}
    last_seen = dict(
        Attempt.objects.filter(user=user).values_list("question_id").annotate(last=Max("created_at"))
    )

    chosen, used = [], set()
    while len(chosen) < n:
        available = [sid for sid, items in by_skill.items() if any(q.id not in used for q in items)]
        if not available:
            break
        weights = [1.05 - mastery.get(sid, DEFAULT_MASTERY) for sid in available]
        sid = rng.choices(available, weights=weights)[0]
        level = mastery.get(sid, DEFAULT_MASTERY)
        target = 1 if level < 0.4 else (2 if level < 0.75 else 3)
        pool = [q for q in by_skill[sid] if q.id not in used]
        pool.sort(
            key=lambda q: (
                q.id in last_seen,
                last_seen[q.id].timestamp() if q.id in last_seen else 0,
                abs(q.difficulty - target),
                rng.random(),
            )
        )
        chosen.append(pool[0])
        used.add(pool[0].id)
    return chosen


def start_session(user, kind, skill=None, count=None, rng=None):
    if kind == PracticeSession.Kind.DAILY:
        goal = Goal.objects.filter(user=user).first()
        count = count or (plan_for(goal).daily_questions if goal else 10)
    else:
        count = count or SKILL_SESSION_LENGTH
    questions = pick_questions(user, count, skill=skill, rng=rng)
    if not questions:
        return None
    return PracticeSession.objects.create(
        user=user, kind=kind, skill=skill, question_ids=[str(q.id) for q in questions]
    )


def resumable_daily_session(user, today=None):
    """Today's unfinished daily set, if the member left in the middle of one."""
    today = today or timezone.localdate()
    session = (
        PracticeSession.objects.filter(
            user=user, kind=PracticeSession.Kind.DAILY, finished_at__isnull=True, started_at__gte=_day_start(today)
        )
        .order_by("-started_at")
        .first()
    )
    return session if session is not None and session.position < session.total else None


# ---------------------------------------------------------------- recording results

@transaction.atomic
def record_attempt(user, question, answer, seconds=0, session=None):
    """Save one answer and update the member's progress. Returns the Attempt.

    Answering the same question twice in one session returns the first attempt.
    """
    if session is not None:
        existing = Attempt.objects.filter(session=session, question=question).first()
        if existing:
            return existing
    is_correct = grade(question, answer)
    try:
        with transaction.atomic():
            attempt = Attempt.objects.create(
                user=user,
                question=question,
                session=session,
                answer=(answer or "").strip()[:100],
                is_correct=is_correct,
                seconds=max(0, min(int(seconds or 0), 3600)),
            )
    except IntegrityError:
        return Attempt.objects.get(session=session, question=question)

    progress, _ = SkillProgress.objects.select_for_update().get_or_create(user=user, skill=question.skill)
    progress.attempts += 1
    progress.correct += int(is_correct)
    progress.mastery = round(progress.mastery * (1 - MASTERY_STEP) + MASTERY_STEP * float(is_correct), 4)
    progress.last_practiced_at = timezone.now()
    progress.save()
    return attempt


def finish_session(session):
    if session.finished_at is None:
        session.finished_at = timezone.now()
        session.save(update_fields=["finished_at", "updated_at"])
        snapshot_score(session.user)
    return session


# ---------------------------------------------------------------- score estimate

def estimate_score(user):
    """PLACEHOLDER estimate on the 400-1600 scale.

    Blends the score the member reported with how they actually do on practice questions
    (hard questions count more). The more they practice, the more practice counts.
    """
    goal = Goal.objects.filter(user=user).first()
    if goal is None:
        return None
    recent = list(Attempt.objects.filter(user=user).select_related("question").order_by("-created_at")[:100])
    total = Attempt.objects.filter(user=user).count()
    if not recent:
        return goal.current_score
    weight_sum = sum(a.question.difficulty for a in recent)
    accuracy = sum(a.question.difficulty for a in recent if a.is_correct) / weight_sum
    from_practice = 400 + 1200 * accuracy
    trust = total / (total + ESTIMATE_PRIOR_WEIGHT)
    blended = goal.current_score * (1 - trust) + from_practice * trust
    return int(max(400, min(1600, round(blended / 10) * 10)))


def snapshot_score(user, on_date=None):
    score = estimate_score(user)
    if score is None:
        return None
    on_date = on_date or timezone.localdate()
    ScoreEstimate.objects.update_or_create(user=user, on_date=on_date, defaults={"score": score})
    return score


# ---------------------------------------------------------------- streaks and daily numbers

def _day_start(day):
    return timezone.make_aware(datetime.combine(day, time.min))


def questions_today(user, today=None):
    today = today or timezone.localdate()
    return Attempt.objects.filter(user=user, created_at__gte=_day_start(today)).count()


def streak(user, today=None):
    """Consecutive days (ending today, or yesterday if nothing yet today) with at least one answer."""
    today = today or timezone.localdate()
    since = _day_start(today - timedelta(days=400))
    days = {
        timezone.localtime(dt).date()
        for dt in Attempt.objects.filter(user=user, created_at__gte=since).datetimes("created_at", "day")
    }
    cursor = today if today in days else today - timedelta(days=1)
    count = 0
    while cursor in days:
        count += 1
        cursor -= timedelta(days=1)
    return count


def daily_series(user, days=14, today=None):
    """[(date, answered, correct)] for the last N days, oldest first."""
    today = today or timezone.localdate()
    start = today - timedelta(days=days - 1)
    rows = defaultdict(lambda: [0, 0])
    for created_at, correct in Attempt.objects.filter(user=user, created_at__gte=_day_start(start)).values_list(
        "created_at", "is_correct"
    ):
        day = timezone.localtime(created_at).date()
        rows[day][0] += 1
        rows[day][1] += int(correct)
    return [(start + timedelta(days=i), *rows[start + timedelta(days=i)]) for i in range(days)]


def skill_rows(user):
    """Every active skill with the member's progress, grouped for the home path."""
    progress = {p.skill_id: p for p in SkillProgress.objects.filter(user=user)}
    result = []
    for skill in Skill.objects.filter(is_active=True).order_by("track", "order", "name"):
        p = progress.get(skill.id)
        if p is None or p.attempts == 0:
            state = "new"
        elif p.mastery >= 0.75 and p.attempts >= 4:
            state = "strong"
        else:
            state = "learning"
        result.append({"skill": skill, "progress": p, "state": state})
    return result
