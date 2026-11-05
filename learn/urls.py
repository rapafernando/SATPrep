from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("onboarding/", views.onboarding, name="onboarding"),
    path("me/", views.me, name="me"),
    path("practice/", views.practice_home, name="practice_home"),
    path("plan/", views.plan, name="plan"),
    path("progress/", views.progress, name="progress"),
    path("family/", views.family, name="family"),
    path("skills/<slug:slug>/", views.skill_detail, name="skill_detail"),
    path("skills/<slug:slug>/practice/", views.start_skill, name="start_skill"),
    path("practice/daily/", views.start_daily, name="start_daily"),
    path("practice/<uuid:session_id>/", views.practice, name="practice"),
    path("practice/<uuid:session_id>/answer/", views.practice_answer, name="practice_answer"),
    path("practice/<uuid:session_id>/skip/", views.practice_skip, name="practice_skip"),
    path("practice/<uuid:session_id>/review/", views.practice_review, name="practice_review"),
    path("practice/<uuid:session_id>/next/", views.practice_next, name="practice_next"),
    path("practice/<uuid:session_id>/done/", views.practice_done, name="practice_done"),
]
