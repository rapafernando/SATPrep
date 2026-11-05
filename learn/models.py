import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Track(models.TextChoices):
    MATH = "math", "Math"
    RW = "rw", "Reading & Writing"


class Skill(models.Model):
    """One topic on the learning path, e.g. 'Linear equations'."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    track = models.CharField(max_length=8, choices=Track.choices)
    domain = models.CharField(max_length=80, help_text="Group heading, e.g. Algebra")
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    order = models.PositiveSmallIntegerField(default=0)
    summary = models.CharField(max_length=200, blank=True)
    lesson = models.TextField(blank=True, help_text="Short lesson shown before practice. Plain text; use $...$ for math.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["track", "order", "name"]
        indexes = [models.Index(fields=["track", "order"])]

    def __str__(self):
        return f"{self.get_track_display()}: {self.name}"


class Question(models.Model):
    class AnswerType(models.TextChoices):
        CHOICE = "choice", "Multiple choice (A-D)"
        NUMERIC = "numeric", "Type in a number"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT, related_name="questions")
    answer_type = models.CharField(max_length=8, choices=AnswerType.choices, default=AnswerType.CHOICE)
    stem = models.TextField(help_text="The question. Plain text; use $...$ for math.")
    choices = models.JSONField(default=list, blank=True, help_text='Multiple choice only: ["text of A", "text of B", ...]')
    correct_answer = models.CharField(
        max_length=100,
        help_text="Multiple choice: the letter (A, B, C or D). Number: the answer; separate alternatives with | (e.g. 1/2|0.5).",
    )
    difficulty = models.PositiveSmallIntegerField(default=2, help_text="1 easy, 2 medium, 3 hard")
    explanation = models.TextField(help_text="Step-by-step worked solution shown after answering.")
    source_note = models.CharField(max_length=120, blank=True, help_text="Where the question came from (be sure you may use it).")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(difficulty__gte=1, difficulty__lte=3), name="question_difficulty_1_to_3"),
            models.CheckConstraint(condition=models.Q(answer_type__in=["choice", "numeric"]), name="question_answer_type_valid"),
        ]
        indexes = [models.Index(fields=["skill", "is_active"])]

    def __str__(self):
        return self.stem[:60]

    @property
    def labelled_choices(self):
        return [(chr(65 + i), text) for i, text in enumerate(self.choices)]


class Goal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goal")
    current_score = models.PositiveSmallIntegerField(help_text="Most recent total score, 400-1600")
    target_score = models.PositiveSmallIntegerField(help_text="Score you want, 400-1600")
    target_school = models.CharField(max_length=120, blank=True)
    test_date = models.DateField()
    minutes_per_day = models.PositiveSmallIntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(current_score__gte=400, current_score__lte=1600), name="goal_current_score_range"
            ),
            models.CheckConstraint(
                condition=models.Q(target_score__gte=400, target_score__lte=1600), name="goal_target_score_range"
            ),
            models.CheckConstraint(
                condition=models.Q(minutes_per_day__gte=5, minutes_per_day__lte=240), name="goal_minutes_range"
            ),
        ]

    def __str__(self):
        return f"{self.user}: {self.current_score} -> {self.target_score}"


class PracticeSession(models.Model):
    class Kind(models.TextChoices):
        DAILY = "daily", "Daily session"
        SKILL = "skill", "Skill practice"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="practice_sessions")
    skill = models.ForeignKey(Skill, null=True, blank=True, on_delete=models.SET_NULL, related_name="sessions")
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.DAILY)
    question_ids = models.JSONField(default=list)
    position = models.PositiveSmallIntegerField(default=0)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["user", "-started_at"])]
        constraints = [models.CheckConstraint(condition=models.Q(kind__in=["daily", "skill"]), name="session_kind_valid")]

    @property
    def total(self):
        return len(self.question_ids)

    @property
    def is_finished(self):
        return self.finished_at is not None

    @property
    def current_question_id(self):
        if self.position < self.total:
            return self.question_ids[self.position]
        return None


class Attempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="attempts")
    session = models.ForeignKey(PracticeSession, null=True, blank=True, on_delete=models.SET_NULL, related_name="attempts")
    answer = models.CharField(max_length=100, blank=True)
    is_correct = models.BooleanField()
    seconds = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["user", "question"]),
            models.Index(fields=["session"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "question"],
                condition=models.Q(session__isnull=False),
                name="attempt_one_per_question_per_session",
            )
        ]


class SkillProgress(models.Model):
    """How well one member knows one skill. mastery is a 0-1 running average."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="skill_progress")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="progress")
    attempts = models.PositiveIntegerField(default=0)
    correct = models.PositiveIntegerField(default=0)
    mastery = models.FloatField(default=0.5)
    last_practiced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "skill"], name="skillprogress_unique"),
            models.CheckConstraint(condition=models.Q(mastery__gte=0, mastery__lte=1), name="skillprogress_mastery_0_1"),
        ]
        indexes = [models.Index(fields=["skill"])]


class ScoreEstimate(models.Model):
    """One predicted-score reading per member per day, for the progress chart."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="score_estimates")
    on_date = models.DateField()
    score = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["on_date"]
        constraints = [
            models.UniqueConstraint(fields=["user", "on_date"], name="scoreestimate_one_per_day"),
            models.CheckConstraint(condition=models.Q(score__gte=400, score__lte=1600), name="scoreestimate_range"),
        ]
