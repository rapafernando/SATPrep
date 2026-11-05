"""Shared fixtures for the browser tests.

Run:   E2E_PYTHON=/path/to/python-with-django  python -m pytest e2e -x -q
Needs: pip install pytest playwright && playwright install chromium
It starts its own throwaway server and SQLite database; it never touches a real one.
"""
import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request

import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("E2E_PORT", "8131"))
BASE = f"http://127.0.0.1:{PORT}"
PW = "Correct-horse-battery-9"
RESULTS = pathlib.Path(__file__).parent / "results.json"
_results = {}


class Db:
    def __init__(self, path):
        self.path = path

    def q(self, sql, *args):
        con = sqlite3.connect(self.path)
        try:
            return con.execute(sql, args).fetchall()
        finally:
            con.close()

    def one(self, sql, *args):
        rows = self.q(sql, *args)
        return rows[0][0] if rows else None

    def run(self, sql, *args):
        con = sqlite3.connect(self.path)
        try:
            con.execute(sql, args)
            con.commit()
        finally:
            con.close()


@pytest.fixture(scope="session", autouse=True)
def server():
    tmp = tempfile.mkdtemp(prefix="e2e-")
    dbfile = os.path.join(tmp, "e2e.sqlite3")
    env = dict(os.environ, DATABASE_URL=f"sqlite:///{dbfile}", SECRET_KEY="e2e-" + "k" * 40, DEBUG="0", HTTPS_ONLY="False",
               ALLOWED_HOSTS="127.0.0.1,localhost", PYTHONDONTWRITEBYTECODE="1")
    env.pop("DJANGO_SETTINGS_MODULE", None)
    py = os.environ.get("E2E_PYTHON", sys.executable)
    subprocess.run([py, "manage.py", "migrate", "-v0"], cwd=ROOT, env=env, check=True)
    subprocess.run([py, "manage.py", "createcachetable"], cwd=ROOT, env=env, check=True)
    # Production-like: DEBUG off, static files collected and served by WhiteNoise, real error pages.
    static_root = ROOT / "staticfiles"
    had_static = static_root.exists()
    subprocess.run([py, "manage.py", "collectstatic", "--noinput", "-v0"], cwd=ROOT, env=env, check=True)
    with open(pathlib.Path(__file__).parent / "seed.py") as f:
        subprocess.run([py, "manage.py", "shell"], cwd=ROOT, env=env, stdin=f, check=True, capture_output=True)
    proc = subprocess.Popen([py, "manage.py", "runserver", f"127.0.0.1:{PORT}", "--noreload"], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=open(os.path.join(tmp, "server.log"), "w"))
    for _ in range(60):
        try:
            urllib.request.urlopen(BASE + "/healthz", timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    else:
        proc.kill()
        raise RuntimeError("server did not start")
    yield Db(dbfile)
    proc.terminate()
    if not had_static:
        import shutil

        shutil.rmtree(static_root, ignore_errors=True)
    log = open(os.path.join(tmp, "server.log")).read()
    (pathlib.Path(__file__).parent / "server.log").write_text(log[-20000:])


@pytest.fixture(scope="session")
def db(server):
    return server


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


class App:
    """One browser context + page that records console errors and 5xx answers."""

    def __init__(self, browser, width=390, height=844, scheme="light", user_agent=None, offline_ok=False):
        kwargs = dict(viewport={"width": width, "height": height}, color_scheme=scheme)
        if user_agent:
            kwargs["user_agent"] = user_agent
        self.ctx = browser.new_context(**kwargs)
        self.page = self.ctx.new_page()
        self.errors = []
        self.allowed = []  # substrings of console errors that a test expects (e.g. a deliberate 404)
        self.page.on("console", lambda m: self.errors.append(m.text) if m.type == "error" else None)
        self.page.on("pageerror", lambda e: self.errors.append("pageerror: " + str(e)))
        self.page.on("response", lambda r: self.errors.append(f"HTTP {r.status} {r.url}") if r.status >= 500 else None)

    def go(self, path):
        return self.page.goto(BASE + path)

    def login(self, username, password=PW, expect_ok=True):
        self.go("/login/")
        self.page.get_by_label("Username").fill(username)
        self.page.get_by_label("Password").fill(password)
        self.page.get_by_role("button", name="Sign in").click()
        self.page.wait_for_load_state("networkidle")
        if expect_ok:
            assert "/login" not in self.page.url, f"login failed for {username}"
        return self

    def post(self, path, form):
        """POST with this browser's real CSRF token, so the server's permission check is what answers."""
        token = next((c["value"] for c in self.ctx.cookies() if c["name"] == "csrftoken"), "")
        return self.page.request.post(BASE + path, form=form, headers={"X-CSRFToken": token, "Referer": BASE + "/"},
                                      max_redirects=0)

    def real_errors(self):
        return [e for e in self.errors if not any(a in e for a in self.allowed)]

    def close(self):
        self.ctx.close()


@pytest.fixture
def make_app(browser):
    apps = []

    def factory(user=None, **kw):
        app = App(browser, **kw)
        apps.append(app)
        if user:
            app.login(user)
        return app

    yield factory
    problems = []
    for a in apps:
        problems += a.real_errors()
        a.close()
    assert not problems, f"console errors or 5xx responses: {problems}"


_counter = {"k": 0, "n": 0}


@pytest.fixture
def kid():
    """A fresh approved member who already has a goal."""
    _counter["k"] += 1
    return f"k{_counter['k'] - 1:02d}"


@pytest.fixture
def newbie():
    """A fresh approved member with no goal yet."""
    _counter["n"] += 1
    return f"n{_counter['n'] - 1:02d}"


def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        _results[report.nodeid] = report.outcome


def pytest_sessionfinish(session, exitstatus):
    RESULTS.write_text(json.dumps(_results, indent=1))
