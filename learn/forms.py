from datetime import timedelta

from django import forms
from django.utils import timezone

from .models import Goal


class GoalForm(forms.ModelForm):
    test_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), label="Test date")

    class Meta:
        model = Goal
        fields = ["current_score", "target_score", "target_school", "test_date", "minutes_per_day"]
        labels = {
            "current_score": "Where are you now? (total score, 400-1600)",
            "target_score": "Your target score (400-1600)",
            "target_school": "Dream school (optional)",
            "minutes_per_day": "Minutes you can study each day",
        }
        widgets = {
            "current_score": forms.NumberInput(attrs={"min": 400, "max": 1600, "step": 10, "inputmode": "numeric"}),
            "target_score": forms.NumberInput(attrs={"min": 400, "max": 1600, "step": 10, "inputmode": "numeric"}),
            "minutes_per_day": forms.NumberInput(attrs={"min": 5, "max": 240, "step": 5, "inputmode": "numeric"}),
        }

    def clean_current_score(self):
        return self._score(self.cleaned_data["current_score"])

    def clean_target_score(self):
        return self._score(self.cleaned_data["target_score"])

    @staticmethod
    def _score(value):
        if not 400 <= value <= 1600:
            raise forms.ValidationError("Scores run from 400 to 1600.")
        return value

    def clean_minutes_per_day(self):
        value = self.cleaned_data["minutes_per_day"]
        if not 5 <= value <= 240:
            raise forms.ValidationError("Choose between 5 and 240 minutes.")
        return value

    def clean_test_date(self):
        value = self.cleaned_data["test_date"]
        today = timezone.localdate()
        if value < today:
            raise forms.ValidationError("Pick a date that has not passed yet.")
        if value > today + timedelta(days=730):
            raise forms.ValidationError("Pick a date within the next two years.")
        return value

    def clean(self):
        cleaned = super().clean()
        current, target = cleaned.get("current_score"), cleaned.get("target_score")
        if current and target and target < current:
            self.add_error("target_score", "Your target should be at or above where you are now.")
        return cleaned
