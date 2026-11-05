import uuid

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.utils import timezone


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Admins created from the command line are trusted: approve them straight away.
        extra_fields.setdefault("approval_status", "approved")
        extra_fields.setdefault("approved_at", timezone.now())
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """A member of the site.

    New sign-ups start as ``pending`` and cannot sign in until an admin approves them.
    ``ad_free`` lets the admin exempt a member from ads if ads are ever switched on.
    ``date_joined`` (from AbstractUser) is the created-at time.
    """

    class Approval(models.TextChoices):
        PENDING = "pending", "Waiting for approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "No access"

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        PARENT = "parent", "Parent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_name = models.CharField(max_length=60, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    approval_status = models.CharField(
        max_length=10, choices=Approval.choices, default=Approval.PENDING, db_index=True
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_users"
    )
    ad_free = models.BooleanField(
        default=False, help_text="Never show ads to this member, even if ads are switched on."
    )
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(approval_status__in=["pending", "approved", "rejected"]),
                name="user_approval_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=["student", "parent"]), name="user_role_valid"
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def name(self):
        return self.display_name or self.username

    @property
    def is_approved(self):
        return self.approval_status == self.Approval.APPROVED

    def approve(self, by=None):
        self.approval_status = self.Approval.APPROVED
        self.approved_at = timezone.now()
        self.approved_by = by
        self.save(update_fields=["approval_status", "approved_at", "approved_by", "updated_at"])

    def reject(self):
        self.approval_status = self.Approval.REJECTED
        self.save(update_fields=["approval_status", "updated_at"])


class ParentLink(models.Model):
    """Lets a parent account see a child's progress. Created by the admin."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="child_links")
    child = models.ForeignKey(User, on_delete=models.CASCADE, related_name="parent_links")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["parent", "child"], name="parentlink_unique_pair"),
            models.CheckConstraint(
                condition=~models.Q(parent=models.F("child")), name="parentlink_not_self"
            ),
        ]
        indexes = [models.Index(fields=["child"])]

    def __str__(self):
        return f"{self.parent} -> {self.child}"
