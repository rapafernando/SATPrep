"""The one place that decides whether a person sees ads.

Ads show only when ALL of these are true:
  1. the admin switched ads on (SiteSettings.ads_enabled),
  2. some ad code has been pasted in (SiteSettings.ad_html),
  3. the viewer is a signed-in, approved member,
  4. the member is NOT marked ad-free.
Ad slots exist only on the home, progress and session-summary pages, never on a question.
"""


def ads_visible_for(user, site):
    if not (site.ads_enabled and site.ad_html.strip()):
        return False
    if not getattr(user, "is_authenticated", False):
        return False
    if not user.is_approved:
        return False
    return not user.ad_free
