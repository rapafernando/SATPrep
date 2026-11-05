import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User

from . import services
from .charts import bar_heights, line_points
from .forms import GoalForm
from .models import Attempt, Goal, PracticeSession, Question, ScoreEstimate, Skill, Track


def _goal_or_none(user):
    return Goal.objects.filter(user=user).first()


def _summary_for(user, today=None):
    """Numbers shown on the home page and on a parent's family page."""
    goal = _goal_or_none(user)
    return {
        "member": user,
        "goal": goal,
        "plan": services.plan_for(goal, today) if goal else None,
        "estimate": services.estimate_score(user),
        "streak": services.streak(user, today),
        "today_count": services.questions_today(user, today),
    }


@login_required
def home(request):
    if _goal_or_none(request.user) is None:
        return redirect("onboarding")
    summary = _summary_for(request.user)
    goal_questions = summary["plan"].daily_questions
    percent = min(100, round(100 * summary["today_count"] / goal_questions)) if goal_questions else 0
    context = {
        **summary,
        "goal_questions": goal_questions,
        "questions_left": max(0, goal_questions - summary["today_count"]),
        "minutes_left": round(max(0, goal_questions - summary["today_count"]) * services.MINUTES_PER_QUESTION),
        "percent_today": percent,
        "ring_dash": round(RING_LENGTH * percent / 100, 1),
        "ring_length": RING_LENGTH,
        "weak_skills": _work_on_next(request.user),
        "has_questions": Question.objects.filter(is_active=True).exists(),
    }
    return render(request, "learn/home.html", context)


RING_LENGTH = round(2 * 3.14159265 * 38, 1)  # circumference of the r=38 progress ring in home.html


def _work_on_next(user, limit=3):
    """The skills to practice next: tried ones with the lowest mastery first, then ones not tried yet."""
    rows = services.skill_rows(user)
    tried = sorted((r for r in rows if r["progress"] and r["progress"].attempts), key=lambda r: r["progress"].mastery)
    fresh = [r for r in rows if r not in tried]
    picked = (tried + fresh)[:limit]
    return [
        {"skill": r["skill"], "state": r["state"], "pct": round(r["progress"].mastery * 100) if r["state"] != "new" else None}
        for r in picked
    ]


@login_required
def practice_home(request):
    """The Practice tab: every skill by track, plus a button for a mixed daily set."""
    rows = services.skill_rows(request.user)
    tracks = [
        {"key": key, "label": label, "rows": [r for r in rows if r["skill"].track == key]}
        for key, label in Track.choices
    ]
    context = {
        "tracks": [t for t in tracks if t["rows"]],
        "has_goal": _goal_or_none(request.user) is not None,
        "has_questions": Question.objects.filter(is_active=True).exists(),
    }
    return render(request, "learn/practice_home.html", context)


@login_required
def me(request):
    """The Me tab: who you are, your goal, and the links that used to crowd the top bar."""
    user = request.user
    context = {
        "goal": _goal_or_none(user),
        "has_family": user.role == User.Role.PARENT or user.child_links.exists(),
    }
    return render(request, "learn/me.html", context)


@login_required
def onboarding(request):
    goal = _goal_or_none(request.user)
    starter = None
    if goal is None:
        starter = {"current_score": 1000, "target_score": 1300, "minutes_per_day": 30,
                   "test_date": timezone.localdate() + datetime.timedelta(days=90)}
    form = GoalForm(request.POST or None, instance=goal, initial=starter)
    if request.method == "POST" and form.is_valid():
        goal = form.save(commit=False)
        goal.user = request.user
        goal.save()
        services.snapshot_score(request.user)
        return redirect("plan")
    return render(request, "learn/onboarding.html", {"form": form, "editing": goal is not None})


@login_required
def plan(request):
    goal = _goal_or_none(request.user)
    if goal is None:
        return redirect("onboarding")
    return render(request, "learn/plan.html", {"goal": goal, "plan": services.plan_for(goal)})


@login_required
def skill_detail(request, slug):
    skill = get_object_or_404(Skill, slug=slug, is_active=True)
    progress = request.user.skill_progress.filter(skill=skill).first()
    return render(
        request,
        "learn/skill.html",
        {"skill": skill, "progress": progress, "question_count": skill.questions.filter(is_active=True).count()},
    )


@login_required
@require_POST
def start_daily(request):
    if _goal_or_none(request.user) is None:
        return redirect("onboarding")
    session = services.resumable_daily_session(request.user) or services.start_session(
        request.user, PracticeSession.Kind.DAILY
    )
    if session is None:
        messages.error(request, "There are no questions yet. Ask the admin to add some.")
        return redirect("home")
    return redirect("practice", session_id=session.id)


@login_required
@require_POST
def start_skill(request, slug):
    skill = get_object_or_404(Skill, slug=slug, is_active=True)
    session = services.start_session(request.user, PracticeSession.Kind.SKILL, skill=skill)
    if session is None:
        messages.error(request, "This skill has no questions yet.")
        return redirect("skill_detail", slug=slug)
    return redirect("practice", session_id=session.id)


def _own_session(request, session_id):
    return get_object_or_404(PracticeSession, pk=session_id, user=request.user)


def _question(session):
    question_id = session.current_question_id
    return Question.objects.select_related("skill").get(pk=question_id) if question_id else None


@login_required
def practice(request, session_id):
    session = _own_session(request, session_id)
    if session.is_finished or session.position >= session.total:
        return redirect("practice_done", session_id=session.id)
    question = _question(session)
    # Already answered but the page was reloaded or the phone went to sleep: show the review.
    if Attempt.objects.filter(session=session, question=question).exists():
        return redirect("practice_review", session_id=session.id)
    return render(
        request,
        "learn/question.html",
        {"session": session, "question": question, "number": session.position + 1, "total": session.total},
    )


@login_required
@require_POST
def practice_answer(request, session_id):
    session = _own_session(request, session_id)
    if session.is_finished:
        return redirect("practice_done", session_id=session.id)
    question = _question(session)
    if question is None:
        return redirect("practice_done", session_id=session.id)
    answer = request.POST.get("answer", "").strip()
    if not answer:
        messages.error(request, "Choose or type an answer first. You can also skip.")
        return redirect("practice", session_id=session.id)
    try:
        seconds = int(request.POST.get("seconds", "0"))
    except ValueError:
        seconds = 0
    services.record_attempt(request.user, question, answer, seconds, session)
    return redirect("practice_review", session_id=session.id)


@login_required
@require_POST
def practice_skip(request, session_id):
    session = _own_session(request, session_id)
    question = _question(session)
    if question is not None and not session.is_finished:
        services.record_attempt(request.user, question, "", 0, session)  # counts as a miss
    return redirect("practice_review", session_id=session.id)


@login_required
def practice_review(request, session_id):
    session = _own_session(request, session_id)
    question = _question(session)
    if question is None:
        return redirect("practice_done", session_id=session.id)
    attempt = Attempt.objects.filter(session=session, question=question).first()
    if attempt is None:
        return redirect("practice", session_id=session.id)
    choices = dict(question.labelled_choices) if question.answer_type == Question.AnswerType.CHOICE else {}
    return render(
        request,
        "learn/review.html",
        {
            "your_text": choices.get(attempt.answer.upper()),
            "right_text": choices.get(question.correct_answer.strip().upper()),
            "session": session,
            "question": question,
            "attempt": attempt,
            "number": session.position + 1,
            "total": session.total,
            "is_last": session.position + 1 >= session.total,
        },
    )


@login_required
@require_POST
def practice_next(request, session_id):
    session = _own_session(request, session_id)
    question = _question(session)
    # Only move on once the current question has been answered.
    if question is not None and Attempt.objects.filter(session=session, question=question).exists():
        session.position += 1
        session.save(update_fields=["position", "updated_at"])
    if session.position >= session.total:
        services.finish_session(session)
        return redirect("practice_done", session_id=session.id)
    return redirect("practice", session_id=session.id)


@login_required
def practice_done(request, session_id):
    session = _own_session(request, session_id)
    if not session.is_finished:
        if session.position >= session.total:
            services.finish_session(session)
        else:
            return redirect("practice", session_id=session.id)
    attempts = list(session.attempts.select_related("question").order_by("created_at"))
    correct = sum(a.is_correct for a in attempts)
    context = {
        "session": session,
        "attempts": attempts,
        "correct": correct,
        "answered": len(attempts),
        "estimate": services.estimate_score(request.user),
        "streak": services.streak(request.user),
        "minutes": round(sum(a.seconds for a in attempts) / 60, 1),
    }
    return render(request, "learn/done.html", context)


@login_required
def progress(request):
    goal = _goal_or_none(request.user)
    if goal is None:
        return redirect("onboarding")
    estimates = list(ScoreEstimate.objects.filter(user=request.user).order_by("on_date")[:60])
    values = [e.score for e in estimates]
    polyline, points = line_points(values, lo=min(values + [goal.current_score]) - 20, hi=max(values + [goal.target_score]) + 20)
    target_y = None
    if values:
        lo = min(values + [goal.current_score]) - 20
        hi = max(values + [goal.target_score]) + 20
        target_y = round(16 + (200 - 32) * (1 - (goal.target_score - lo) / (hi - lo)), 1)
    series = services.daily_series(request.user, 14)
    heights = bar_heights([s[1] for s in series])
    bars = [
        {"day": day, "answered": answered, "correct": correct, "height": h, "y": 110 - h, "x": 8 + i * 42}
        for i, ((day, answered, correct), h) in enumerate(zip(series, heights))
    ]
    context = {
        "goal": goal,
        "estimate": services.estimate_score(request.user),
        "estimates": estimates,
        "polyline": polyline,
        "points": points,
        "target_y": target_y,
        "bars": bars,
        "gain": (services.estimate_score(request.user) or goal.current_score) - goal.current_score,
        "last14_total": sum(s[1] for s in series),
        "streak": services.streak(request.user),
        "skills": [r for r in services.skill_rows(request.user) if r["progress"]],
        "total_answered": Attempt.objects.filter(user=request.user).count(),
    }
    return render(request, "learn/progress.html", context)


@login_required
def family(request):
    children = list(User.objects.filter(parent_links__parent=request.user, approval_status="approved").order_by("display_name", "username"))
    if not children and request.user.role != User.Role.PARENT:
        raise Http404
    today = timezone.localdate()
    cards = []
    for child in children:
        card = _summary_for(child, today)
        series = services.daily_series(child, 7, today)
        card["week_answered"] = sum(s[1] for s in series)
        card["week_correct"] = sum(s[2] for s in series)
        cards.append(card)
    return render(request, "learn/family.html", {"cards": cards})
