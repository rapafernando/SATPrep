from django.contrib import admin

from .models import Attempt, Goal, Question, ScoreEstimate, Skill


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "track", "domain", "order", "is_active")
    list_filter = ("track", "is_active")
    search_fields = ("name", "domain")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("track", "order")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("short_stem", "skill", "answer_type", "difficulty", "is_active")
    list_filter = ("skill__track", "skill", "answer_type", "difficulty", "is_active")
    search_fields = ("stem", "explanation")
    list_editable = ("is_active",)

    @admin.display(description="Question")
    def short_stem(self, obj):
        return obj.stem[:80]


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("user", "current_score", "target_score", "test_date", "minutes_per_day")
    search_fields = ("user__username",)


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "is_correct", "seconds")
    list_filter = ("is_correct",)
    search_fields = ("user__username",)
    date_hierarchy = "created_at"


@admin.register(ScoreEstimate)
class ScoreEstimateAdmin(admin.ModelAdmin):
    list_display = ("user", "on_date", "score")
