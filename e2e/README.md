# Browser tests

Playwright (Python) tests that click through every flow of the clone. They start their own throwaway server
(DEBUG off, static files collected, fresh SQLite, fake people) and never touch a real database.

    pip install pytest playwright && playwright install chromium
    E2E_PYTHON=/path/to/python-with-Django-installed python -m pytest e2e
    python e2e/report.py        # rewrites replica/test-plan.md from the results

`cases.py` is the test plan. A test named `test_F03_E5_...` covers case F03-E5. Every test also fails on any
console error or 5xx response. `vendor/axe.min.js` is axe-core (MPL-2.0) for the accessibility scans.
