import datetime
import random

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import ParentLink
from accounts.tests import make_user

from . import services
from .models import Attempt, Goal, PracticeSession, Question, ScoreEstimate, Skill, SkillProgress


def goal_for(user, current=1000, target=1200, days=60, minutes=30):
    return Goal.objects.create(user=user, current_score=current, target_score=target,
                               test_date=timezone.localdate() + datetime.timedelta(days=days), minutes_per_day=minutes)


class GradingTests(TestCase):
    def setUp(self):
        skill = Skill.objects.create(track="math", domain="Algebra", name="S", slug="s")
        self.mc = Question.objects.create(skill=skill, answer_type="choice", stem="q", choices=["a", "b", "c", "d"],
                                          correct_answer="C", explanation="e")
        self.num = Question.objects.create(skill=skill, answer_type="numeric", stem="q", correct_answer="1/2|0.5",
                                           explanation="e")
        self.pct = Question.objects.create(skill=skill, answer_type="numeric", stem="q", correct_answer="-3",
                                           explanation="e")

    def test_choice(self):
        self.assertTrue(services.grade(self.mc, "c"))
        self.assertTrue(services.grade(self.mc, " C "))
        self.assertFalse(services.grade(self.mc, "A"))
        self.assertFalse(services.grade(self.mc, ""))

    def test_numeric_equivalents(self):
        for ok in ("1/2", "0.5", ".5", "2/4", " 0.50 "):
            self.assertTrue(services.grade(self.num, ok), ok)
        for bad in ("1/3", "", "abc", "1/0", "0.51"):
            self.assertFalse(services.grade(self.num, bad), bad)

    def test_negative_and_commas(self):
        self.assertTrue(services.grade(self.pct, "-3"))
        self.assertTrue(services.grade(self.pct, "-3.0"))
        self.assertFalse(services.grade(self.pct, "3"))


class PlanTests(TestCase):
    def test_daily_questions_clamped(self):
        u = make_user("p")
        self.assertEqual(services.plan_for(goal_for(u, minutes=30)).daily_questions, 20)
        Goal.objects.all().delete()
        self.assertEqual(services.plan_for(goal_for(u, minutes=5)).daily_questions, 5)
        Goal.objects.all().delete()
        self.assertEqual(services.plan_for(goal_for(u, minutes=240)).daily_questions, 60)

    def test_notes(self):
        u = make_user("p")
        g = goal_for(u, current=1000, target=1000)
        self.assertIn("already at your target", services.plan_for(g).note)
        g.target_score, g.test_date = 1500, timezone.localdate() + datetime.timedelta(days=14)
        self.assertIn("ambitious", services.plan_for(g).note)


class PracticeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", verbosity=0)

    def setUp(self):
        self.user = make_user("kid")
        goal_for(self.user)

    def test_seed_is_idempotent(self):
        n = Question.objects.count()
        call_command("seed_content", verbosity=0)
        self.assertEqual(Question.objects.count(), n)
        self.assertEqual(n, 24)

    def test_pick_no_repeats_and_prefers_weak_skills(self):
        qs = services.pick_questions(self.user, 10, rng=random.Random(1))
        self.assertEqual(len(qs), len({q.id for q in qs}))
        weak, strong = Skill.objects.order_by("slug")[:2]
        SkillProgress.objects.create(user=self.user, skill=weak, mastery=0.05, attempts=10, correct=0)
        SkillProgress.objects.create(user=self.user, skill=strong, mastery=0.98, attempts=10, correct=10)
        counts = {weak.id: 0, strong.id: 0}
        for seed in range(60):
            for q in services.pick_questions(self.user, 4, rng=random.Random(seed)):
                if q.skill_id in counts:
                    counts[q.skill_id] += 1
        self.assertGreater(counts[weak.id], counts[strong.id])

    def test_pick_caps_at_available(self):
        skill = Skill.objects.first()
        n = skill.questions.filter(is_active=True).count()
        self.assertEqual(len(services.pick_questions(self.user, 99, skill=skill)), n)

    def test_empty_bank_returns_none(self):
        Question.objects.update(is_active=False)
        self.assertIsNone(services.start_session(self.user, "daily"))

    def test_record_attempt_updates_mastery_once_per_session(self):
        session = services.start_session(self.user, "daily", count=3)
        q = Question.objects.get(pk=session.question_ids[0])
        a1 = services.record_attempt(self.user, q, q.correct_answer.split("|")[0], 5, session)
        a2 = services.record_attempt(self.user, q, "wrong", 5, session)
        self.assertEqual(a1.pk, a2.pk)
        self.assertTrue(a1.is_correct)
        prog = SkillProgress.objects.get(user=self.user, skill=q.skill)
        self.assertEqual((prog.attempts, prog.correct), (1, 1))
        self.assertAlmostEqual(prog.mastery, 0.5 * 0.75 + 0.25, places=3)

    def test_estimate_moves_with_accuracy_and_is_clamped(self):
        self.assertEqual(services.estimate_score(self.user), 1000)
        q = Question.objects.first()
        for _ in range(200):
            Attempt.objects.create(user=self.user, question=q, answer="x", is_correct=True, seconds=1)
        high = services.estimate_score(self.user)
        self.assertGreater(high, 1000)
        self.assertLessEqual(high, 1600)
        self.assertEqual(high % 10, 0)
        Attempt.objects.all().update(is_correct=False)
        self.assertLess(services.estimate_score(self.user), 1000)

    def test_streak(self):
        q = Question.objects.first()
        today = timezone.localdate()
        for back in (0, 1, 2, 4):
            a = Attempt.objects.create(user=self.user, question=q, answer="x", is_correct=True)
            Attempt.objects.filter(pk=a.pk).update(created_at=timezone.now() - datetime.timedelta(days=back))
        self.assertEqual(services.streak(self.user, today), 3)

    def test_streak_survives_empty_today(self):
        q = Question.objects.first()
        for back in (1, 2):
            a = Attempt.objects.create(user=self.user, question=q, answer="x", is_correct=True)
            Attempt.objects.filter(pk=a.pk).update(created_at=timezone.now() - datetime.timedelta(days=back))
        self.assertEqual(services.streak(self.user), 2)

    def test_full_session_through_views(self):
        self.client.force_login(self.user)
        r = self.client.post(reverse("start_daily"))
        self.assertEqual(r.status_code, 302)
        session = PracticeSession.objects.get(user=self.user)
        total = session.total
        self.assertEqual(total, 20)
        for i in range(total):
            r = self.client.get(reverse("practice", args=[session.id]))
            self.assertEqual(r.status_code, 200, i)
            q = Question.objects.get(pk=session.question_ids[i])
            right = q.correct_answer.split("|")[0]
            self.client.post(reverse("practice_answer", args=[session.id]), {"answer": right, "seconds": "7"})
            # double-submit (phone retry) must not double count
            self.client.post(reverse("practice_answer", args=[session.id]), {"answer": "zzz", "seconds": "7"})
            r = self.client.get(reverse("practice_review", args=[session.id]))
            self.assertEqual(r.status_code, 200)
            r = self.client.post(reverse("practice_next", args=[session.id]))
        self.assertRedirects(r, reverse("practice_done", args=[session.id]), fetch_redirect_response=False)
        session.refresh_from_db()
        self.assertTrue(session.is_finished)
        self.assertEqual(Attempt.objects.filter(user=self.user).count(), total)
        self.assertTrue(Attempt.objects.filter(user=self.user, is_correct=True).count() == total)
        self.assertTrue(ScoreEstimate.objects.filter(user=self.user).exists())
        self.assertEqual(self.client.get(reverse("practice_done", args=[session.id])).status_code, 200)
        self.assertEqual(self.client.get(reverse("progress")).status_code, 200)
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_next_without_answer_does_not_advance(self):
        self.client.force_login(self.user)
        self.client.post(reverse("start_daily"))
        session = PracticeSession.objects.get(user=self.user)
        self.client.post(reverse("practice_next", args=[session.id]))
        session.refresh_from_db()
        self.assertEqual(session.position, 0)

    def test_skip_counts_as_miss_and_empty_answer_is_refused(self):
        self.client.force_login(self.user)
        self.client.post(reverse("start_daily"))
        session = PracticeSession.objects.get(user=self.user)
        self.client.post(reverse("practice_answer", args=[session.id]), {"answer": ""})
        self.assertEqual(Attempt.objects.count(), 0)
        self.client.post(reverse("practice_skip", args=[session.id]))
        self.assertFalse(Attempt.objects.get().is_correct)

    def test_skill_session(self):
        self.client.force_login(self.user)
        skill = Skill.objects.get(slug="linear-equations")
        self.assertEqual(self.client.get(reverse("skill_detail", args=[skill.slug])).status_code, 200)
        self.client.post(reverse("start_skill", args=[skill.slug]))
        session = PracticeSession.objects.get(user=self.user)
        self.assertTrue(all(Question.objects.get(pk=i).skill_id == skill.id for i in session.question_ids))

    def test_cannot_open_someone_elses_session(self):
        other = make_user("other")
        goal_for(other)
        session = services.start_session(other, "daily", count=3)
        self.client.force_login(self.user)
        for name in ("practice", "practice_review", "practice_done"):
            self.assertEqual(self.client.get(reverse(name, args=[session.id])).status_code, 404, name)
        self.assertEqual(self.client.post(reverse("practice_answer", args=[session.id]), {"answer": "A"}).status_code, 404)


class OnboardingTests(TestCase):
    def setUp(self):
        self.user = make_user("kid")
        self.client.force_login(self.user)

    def post(self, **over):
        data = {"current_score": 1000, "target_score": 1300, "target_school": "",
                "test_date": (timezone.localdate() + datetime.timedelta(days=90)).isoformat(), "minutes_per_day": 30}
        data.update(over)
        return self.client.post(reverse("onboarding"), data)

    def test_home_sends_new_member_to_onboarding(self):
        self.assertRedirects(self.client.get(reverse("home")), reverse("onboarding"), fetch_redirect_response=False)

    def test_creates_goal_and_snapshot(self):
        self.assertRedirects(self.post(), reverse("plan"), fetch_redirect_response=False)
        self.assertEqual(Goal.objects.get(user=self.user).target_score, 1300)
        self.assertEqual(ScoreEstimate.objects.get(user=self.user).score, 1000)
        self.assertEqual(self.client.get(reverse("plan")).status_code, 200)

    def test_editing_goal_does_not_duplicate(self):
        self.post()
        self.post(target_score=1400)
        self.assertEqual(Goal.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Goal.objects.get(user=self.user).target_score, 1400)

    def test_validation(self):
        for bad in ({"current_score": 300}, {"target_score": 1700}, {"target_score": 900},
                    {"minutes_per_day": 1}, {"test_date": "2000-01-01"}):
            self.assertEqual(self.post(**bad).status_code, 200, bad)
        self.assertFalse(Goal.objects.exists())


class FamilyTests(TestCase):
    def setUp(self):
        self.parent = make_user("mom", role="parent")
        self.kid = make_user("kid")
        self.stranger = make_user("friend")
        goal_for(self.kid)
        ParentLink.objects.create(parent=self.parent, child=self.kid)

    def test_parent_sees_only_linked_child(self):
        self.client.force_login(self.parent)
        r = self.client.get(reverse("family"))
        self.assertContains(r, "Kid")
        self.assertNotContains(r, "Friend")

    def test_student_without_children_gets_404(self):
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(reverse("family")).status_code, 404)

    def test_parent_without_link_sees_empty_page(self):
        lonely = make_user("dad", role="parent")
        self.client.force_login(lonely)
        self.assertEqual(self.client.get(reverse("family")).status_code, 200)

    def test_parent_cannot_open_child_practice_session(self):
        session = services.start_session(self.kid, "daily", count=2) if Question.objects.exists() else None
        call_command("seed_content", verbosity=0)
        session = services.start_session(self.kid, "daily", count=2)
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(reverse("practice", args=[session.id])).status_code, 404)


class SeedContentTests(TestCase):
    """Guards against a dollar amount like "$40" being read as the start of a math span."""

    def test_math_delimiters_are_balanced_and_never_swallow_prose(self):
        import json
        import re
        from pathlib import Path

        data = json.loads((Path(__file__).parent / "data" / "sample_questions.json").read_text(encoding="utf-8"))
        prose = re.compile(r"[A-Za-z]{3,}\s+[A-Za-z]{3,}\s+[A-Za-z]{3,}")
        for skill in data["skills"]:
            for q in skill["questions"]:
                for text in [q["stem"], q["explanation"], *q.get("choices", [])]:
                    plain = text.replace("\\$", "")
                    self.assertEqual(plain.count("$") % 2, 0, text)
                    for i, chunk in enumerate(plain.split("$")):
                        if i % 2 == 1:
                            self.assertIsNone(prose.search(chunk), f"English words inside math: {text}")
                            # A real math span never starts or ends with a space; a swallowed "$40 fee plus $" does.
                            self.assertEqual(chunk, chunk.strip(), f"Dollar sign read as math delimiter: {text}")


class ShellScreenTests(TestCase):
    """The tab bar, Me, Practice and the focus-mode question screen."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", verbosity=0)

    def setUp(self):
        self.user = make_user("kid")
        goal_for(self.user)
        self.client.force_login(self.user)

    def test_tab_bar_lists_four_tabs_with_current_marked(self):
        html = self.client.get(reverse("progress")).content.decode()
        self.assertIn('class="tabbar"', html)
        for label in ("Today", "Practice", "Progress", "Me"):
            self.assertIn(label, html)
        self.assertIn('aria-current="page"', html)

    def test_anonymous_gets_no_tab_bar(self):
        self.client.logout()
        self.assertNotIn('class="tabbar"', self.client.get(reverse("login")).content.decode())

    def test_me_and_practice_home_render(self):
        self.assertEqual(self.client.get(reverse("me")).status_code, 200)
        r = self.client.get(reverse("practice_home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Linear equations")

    def test_me_and_practice_need_login(self):
        self.client.logout()
        for name in ("me", "practice_home", "progress"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 302, name)

    def test_question_page_skip_is_a_separate_form(self):
        self.client.post(reverse("start_daily"))
        session = PracticeSession.objects.get(user=self.user)
        html = self.client.get(reverse("practice", args=[session.id])).content.decode()
        self.assertIn('id="skip-form"', html)
        self.assertIn('form="skip-form"', html)
        self.assertIn('id="check-btn"', html)

    def test_review_shows_wrong_answer_words_not_just_colour(self):
        self.client.post(reverse("start_daily"))
        session = PracticeSession.objects.get(user=self.user)
        self.client.post(reverse("practice_answer", args=[session.id]), {"answer": "definitely-wrong-zzz"})
        r = self.client.get(reverse("practice_review", args=[session.id]))
        self.assertContains(r, "Not quite")
        html = r.content.decode().lower()  # choice questions show the letter in capitals, numeric ones the text
        self.assertIn("you chose", html)
        self.assertIn("definitely-wrong-zzz", html)

    def test_progress_empty_state(self):
        r = self.client.get(reverse("progress"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Predicted score")


class GoalDefaultsTests(TestCase):
    def test_new_member_sees_starting_values(self):
        u = make_user("fresh")
        self.client.force_login(u)
        r = self.client.get(reverse("onboarding"))
        self.assertContains(r, 'value="1300"')
        self.assertContains(r, 'value="30"')


class ResumeTests(TestCase):
    """BUG-001: leaving mid-set and pressing Keep going must come back to the same set."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", verbosity=0)

    def setUp(self):
        self.user = make_user("kid")
        goal_for(self.user)
        self.client.force_login(self.user)

    def test_start_daily_resumes_unfinished_set_from_today(self):
        first = self.client.post(reverse("start_daily"))
        session = PracticeSession.objects.get(user=self.user)
        PracticeSession.objects.filter(pk=session.pk).update(position=3)
        again = self.client.post(reverse("start_daily"))
        self.assertEqual(first.url, again.url)
        self.assertEqual(PracticeSession.objects.filter(user=self.user).count(), 1)

    def test_start_daily_starts_fresh_after_a_finished_set(self):
        self.client.post(reverse("start_daily"))
        session = PracticeSession.objects.get(user=self.user)
        PracticeSession.objects.filter(pk=session.pk).update(finished_at=timezone.now())
        self.client.post(reverse("start_daily"))
        self.assertEqual(PracticeSession.objects.filter(user=self.user).count(), 2)

    def test_yesterdays_unfinished_set_is_not_resumed(self):
        self.client.post(reverse("start_daily"))
        session = PracticeSession.objects.get(user=self.user)
        PracticeSession.objects.filter(pk=session.pk).update(started_at=timezone.now() - datetime.timedelta(days=1, hours=2))
        self.client.post(reverse("start_daily"))
        self.assertEqual(PracticeSession.objects.filter(user=self.user).count(), 2)

    def test_another_members_set_is_never_resumed(self):
        other = make_user("other")
        goal_for(other)
        self.client.post(reverse("start_daily"))
        self.client.force_login(other)
        self.client.post(reverse("start_daily"))
        self.assertEqual(PracticeSession.objects.count(), 2)

    def test_practice_tab_without_goal_explains_the_mixed_set(self):
        fresh = make_user("fresh")
        self.client.force_login(fresh)
        self.assertContains(self.client.get(reverse("practice_home")), "Set your goal first")
