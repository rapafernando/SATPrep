from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils import timezone

from .models import ParentLink, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username", "display_name", "role", "approval_status", "ad_free", "is_staff", "date_joined", "last_login",
    )
    list_filter = ("approval_status", "ad_free", "role", "is_staff")
    search_fields = ("username", "display_name", "email")
    ordering = ("-date_joined",)
    readonly_fields = ("approved_at", "approved_by", "last_login", "date_joined")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Membership", {"fields": ("display_name", "role", "approval_status", "approved_at", "approved_by", "ad_free")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Membership", {"fields": ("display_name", "role", "approval_status", "ad_free")}),
    )
    actions = ["approve_selected", "reject_selected", "set_ad_free", "clear_ad_free"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Accounts the admin creates by hand are trusted: approve unless told otherwise.
        if not change and obj.approval_status == User.Approval.PENDING:
            obj.approve(by=request.user)

    @admin.action(description="Approve selected members")
    def approve_selected(self, request, queryset):
        now = timezone.now()
        count = queryset.update(
            approval_status=User.Approval.APPROVED, approved_at=now, approved_by=request.user, updated_at=now
        )
        self.message_user(request, f"Approved {count} member(s).")

    @admin.action(description="Remove access for selected members")
    def reject_selected(self, request, queryset):
        queryset = queryset.exclude(pk=request.user.pk)  # never lock yourself out
        count = queryset.update(approval_status=User.Approval.REJECTED, updated_at=timezone.now())
        self.message_user(request, f"Removed access for {count} member(s).")

    @admin.action(description="Make selected members ad-free")
    def set_ad_free(self, request, queryset):
        count = queryset.update(ad_free=True, updated_at=timezone.now())
        self.message_user(request, f"{count} member(s) are now ad-free.")

    @admin.action(description="Show ads to selected members again")
    def clear_ad_free(self, request, queryset):
        count = queryset.update(ad_free=False, updated_at=timezone.now())
        self.message_user(request, f"{count} member(s) will see ads when ads are on.")


@admin.register(ParentLink)
class ParentLinkAdmin(admin.ModelAdmin):
    list_display = ("parent", "child", "created_at")
    autocomplete_fields = ("parent", "child")
    search_fields = ("parent__username", "child__username")
