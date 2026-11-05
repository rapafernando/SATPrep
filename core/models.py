import uuid

from django.db import models


class SiteSettings(models.Model):
    """One row of site-wide switches, edited from the admin console."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Enforces "only one row": unique + must be true.
    singleton = models.BooleanField(default=True, editable=False, unique=True)

    signups_open = models.BooleanField(
        default=True, help_text="When off, the sign-up page tells visitors that sign-ups are closed."
    )
    ads_enabled = models.BooleanField(
        default=False,
        help_text="Master switch for ads. Off by default. Members marked ad-free never see ads.",
    )
    ad_label = models.CharField(max_length=40, default="Sponsored", blank=True)
    ad_html = models.TextField(
        blank=True,
        help_text="Ad code from your ad network (trusted HTML, pasted exactly as given). Shown only where an ad slot exists.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"
        constraints = [
            models.CheckConstraint(condition=models.Q(singleton=True), name="sitesettings_single_row"),
        ]

    def __str__(self):
        return "Site settings"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(singleton=True)
        return obj
