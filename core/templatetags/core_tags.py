from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def ad_slot(context):
    """Renders the admin's ad code, or nothing. See core/ads.py for the rules."""
    if not context.get("show_ads"):
        return ""
    site = context["site"]
    label = site.ad_label
    html = '<aside class="ad-slot" aria-label="Advertisement">'
    if label:
        from django.utils.html import escape

        html += f'<small class="ad-label">{escape(label)}</small>'
    # ad_html is trusted HTML pasted by the admin from their ad network.
    html += f"<div>{site.ad_html}</div></aside>"
    return mark_safe(html)


@register.simple_tag
def pending_count():
    """How many sign-ups wait for approval (shown as a badge in the admin console)."""
    from accounts.models import User

    return User.objects.filter(approval_status="pending").count()
