"""Unit tests for the Kiro hook scripts in scripts/hooks/.

Each hook is exercised two ways:
  - as a function (import the module, call main()/helpers with a patched stdin
    and tmp_path), and
  - as a subprocess where the stdin-JSON contract and exit code matter most
    (the guards that exit 2 to block a tool call).

Repo root is derived from this file so the tests run from anywhere.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / "scripts" / "hooks"


def _load(mod_name: str):
    """Import a hook script by path (scripts/hooks is not a package)."""
    mod_key = f"hooks_{mod_name}"
    path = HOOKS_DIR / f"{mod_name}.py"
    spec = importlib.util.spec_from_file_location(mod_key, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Register before exec so @dataclass can resolve string (PEP 563) annotations
    # via sys.modules[cls.__module__]; a hook run directly as __main__ never hits
    # this path.
    sys.modules[mod_key] = module
    spec.loader.exec_module(module)
    return module


def _run(script: str, stdin_obj, argv=None, env_extra=None):
    """Run a hook as a subprocess, feeding JSON on stdin. Returns CompletedProcess."""
    cmd = [sys.executable, str(HOOKS_DIR / f"{script}.py")] + list(argv or [])
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    payload = "" if stdin_obj is None else json.dumps(stdin_obj)
    return subprocess.run(
        cmd, input=payload, capture_output=True, text=True, env=env, timeout=30
    )


# --------------------------------------------------------------------------- #
# #2 remind_templates
# --------------------------------------------------------------------------- #
class TestRemindTemplates:
    def test_prints_reminder_and_exits_zero(self):
        cp = _run("remind_templates", {"hook_event_name": "userPromptSubmit"})
        assert cp.returncode == 0
        assert "reviewed templates" in cp.stdout.lower()

    def test_ok_with_empty_stdin(self):
        cp = _run("remind_templates", None)
        assert cp.returncode == 0
        assert cp.stdout.strip() != ""


# --------------------------------------------------------------------------- #
# #3 guard_templates
# --------------------------------------------------------------------------- #
class TestGuardTemplates:
    def _event(self, path, cwd):
        return {
            "hook_event_name": "preToolUse",
            "cwd": str(cwd),
            "tool_name": "fs_write",
            "tool_input": {"path": path},
        }

    def _git_repo(self, tmp_path: Path) -> Path:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / "planner" / "templates" / "en").mkdir(parents=True)
        (tmp_path / "planner" / "templates" / "signoff.json").write_text("{}\n")
        (tmp_path / "planner" / "templates" / "en" / "itinerary.md").write_text("hi\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
            cwd=tmp_path, check=True,
        )
        return tmp_path

    def test_non_template_write_allowed(self, tmp_path):
        repo = self._git_repo(tmp_path)
        cp = _run("guard_templates", self._event("engine/router.py", repo))
        assert cp.returncode == 0

    def test_template_write_without_signoff_blocked(self, tmp_path):
        repo = self._git_repo(tmp_path)
        cp = _run("guard_templates", self._event("planner/templates/en/itinerary.md", repo))
        assert cp.returncode == 2
        assert "signoff.json" in cp.stderr
        assert "BLOCKED" in cp.stderr

    def test_template_write_with_signoff_in_same_write_allowed(self, tmp_path):
        repo = self._git_repo(tmp_path)
        ev = {
            "hook_event_name": "preToolUse",
            "cwd": str(repo),
            "tool_name": "fs_write",
            "tool_input": {"paths": [
                "planner/templates/en/itinerary.md",
                "planner/templates/signoff.json",
            ]},
        }
        cp = _run("guard_templates", ev)
        assert cp.returncode == 0

    def test_template_write_with_signoff_dirty_in_worktree_allowed(self, tmp_path):
        repo = self._git_repo(tmp_path)
        # dirty the signoff file in the working tree
        (repo / "planner" / "templates" / "signoff.json").write_text('{"x":1}\n')
        cp = _run("guard_templates", self._event("planner/templates/en/itinerary.md", repo))
        assert cp.returncode == 0

    def test_malformed_json_fails_open(self, tmp_path):
        cp = subprocess.run(
            [sys.executable, str(HOOKS_DIR / "guard_templates.py")],
            input="not json {{{", capture_output=True, text=True, timeout=30,
        )
        assert cp.returncode == 0  # fail open, do not block on bad payload


# --------------------------------------------------------------------------- #
# #4 block_live_routing
# --------------------------------------------------------------------------- #
class TestBlockLiveRouting:
    def _shell(self, command):
        return {"hook_event_name": "preToolUse", "tool_name": "execute_bash",
                "tool_input": {"command": command}}

    def _web(self, url):
        return {"hook_event_name": "preToolUse", "tool_name": "web_fetch",
                "tool_input": {"url": url}}

    @pytest.mark.parametrize("command", [
        "curl https://maps.googleapis.com/maps/api/directions/json?origin=a",
        "curl http://router.project-osrm.org/route/v1/driving/-72,42;-72,43",
        "python -c 'import osrm'",
    ])
    def test_blocks_live_routing_shell(self, command):
        cp = _run("block_live_routing", self._shell(command))
        assert cp.returncode == 2
        assert "use gtfs-mcp" in cp.stderr

    def test_blocks_mapbox_directions(self):
        cp = _run("block_live_routing",
                  self._web("https://api.mapbox.com/directions/v5/mapbox/driving/x"))
        assert cp.returncode == 2
        assert "use gtfs-mcp" in cp.stderr

    def test_allows_plain_mapbox_tiles(self):
        # a non-routing mapbox URL (tiles) must NOT be blocked
        cp = _run("block_live_routing",
                  self._web("https://api.mapbox.com/styles/v1/mapbox/streets-v11"))
        assert cp.returncode == 0

    def test_allows_innocuous_shell(self):
        cp = _run("block_live_routing", self._shell("pytest -q && echo done"))
        assert cp.returncode == 0

    def test_empty_input_allows(self):
        cp = _run("block_live_routing", None)
        assert cp.returncode == 0


# --------------------------------------------------------------------------- #
# #5 log_provenance
# --------------------------------------------------------------------------- #
class TestLogProvenance:
    def test_appends_one_line_with_sources(self, tmp_path):
        log = tmp_path / "docs" / "provenance.jsonl"
        ev = {
            "hook_event_name": "postToolUse",
            "tool_name": "@gtfs-mcp/trip_plan",
            "tool_input": {"origin": "A", "dest": "B"},
            "tool_response": {"sources": [{"feed": "pvta", "vintage": "2026-10"}]},
            "session_id": "sess-1",
        }
        cp = _run("log_provenance", ev, env_extra={"PROVENANCE_LOG": str(log)})
        assert cp.returncode == 0
        lines = log.read_text().strip().splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["tool"] == "@gtfs-mcp/trip_plan"
        assert rec["input"] == {"origin": "A", "dest": "B"}
        assert rec["sources"] == [{"feed": "pvta", "vintage": "2026-10"}]
        assert rec["session"] == "sess-1"
        assert rec["ts"].endswith("Z")

    def test_omits_sources_when_absent_and_appends(self, tmp_path):
        log = tmp_path / "provenance.jsonl"
        ev1 = {"tool_name": "@gtfs-mcp/stops", "tool_input": {}, "tool_response": {}}
        ev2 = {"tool_name": "@gtfs-mcp/routes", "tool_input": {"q": 1}}
        _run("log_provenance", ev1, env_extra={"PROVENANCE_LOG": str(log)})
        _run("log_provenance", ev2, env_extra={"PROVENANCE_LOG": str(log)})
        lines = log.read_text().strip().splitlines()
        assert len(lines) == 2  # appended, not overwritten
        assert "sources" not in json.loads(lines[0])
        assert json.loads(lines[1])["session"] is None

    def test_empty_stdin_is_noop(self, tmp_path):
        log = tmp_path / "p.jsonl"
        cp = _run("log_provenance", None, env_extra={"PROVENANCE_LOG": str(log)})
        assert cp.returncode == 0
        assert not log.exists()

    def test_resulting_file_is_valid_jsonl(self, tmp_path):
        log = tmp_path / "p.jsonl"
        for i in range(3):
            _run("log_provenance", {"tool_name": f"@gtfs-mcp/t{i}", "tool_input": {}},
                 env_extra={"PROVENANCE_LOG": str(log)})
        for line in log.read_text().splitlines():
            json.loads(line)  # each line parses


# --------------------------------------------------------------------------- #
# #8 validate_gtfs
# --------------------------------------------------------------------------- #
def _write_min_feed(d: Path, bad_time: bool = False, missing: str | None = None):
    d.mkdir(parents=True, exist_ok=True)
    files = {
        "stops.txt": "stop_id,stop_lat,stop_lon\nS1,42.0,-72.0\n",
        "routes.txt": "route_id,route_type\nR1,3\n",
        "trips.txt": "route_id,service_id,trip_id\nR1,SVC,T1\n",
        "stop_times.txt": (
            "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
            + ("T1,notatime,08:00:00,S1,1\n" if bad_time
               else "T1,25:10:00,25:10:00,S1,1\n")  # >24h allowed
        ),
        "calendar.txt": "service_id,monday,start_date,end_date\nSVC,1,20260101,20270101\n",
    }
    if missing:
        files.pop(missing + ".txt", None)
    for name, text in files.items():
        (d / name).write_text(text)


class TestValidateGtfs:
    def test_valid_dir_feed_over24h_ok(self, tmp_path):
        feed = tmp_path / "gtfs"
        _write_min_feed(feed)
        mod = _load("validate_gtfs")
        problems = mod.validate(feed)
        assert problems == [], problems

    def test_cli_exit_zero_on_valid(self, tmp_path):
        feed = tmp_path / "gtfs"
        _write_min_feed(feed)
        cp = subprocess.run(
            [sys.executable, str(HOOKS_DIR / "validate_gtfs.py"), str(feed)],
            capture_output=True, text=True, timeout=30,
        )
        assert cp.returncode == 0
        assert "OK" in cp.stdout

    def test_missing_required_file(self, tmp_path):
        feed = tmp_path / "gtfs"
        _write_min_feed(feed, missing="routes")
        mod = _load("validate_gtfs")
        problems = mod.validate(feed)
        assert any("routes.txt" in p for p in problems)

    def test_calendar_dates_satisfies_calendar(self, tmp_path):
        feed = tmp_path / "gtfs"
        _write_min_feed(feed, missing="calendar")
        (feed / "calendar_dates.txt").write_text(
            "service_id,date,exception_type\nSVC,20260101,1\n")
        mod = _load("validate_gtfs")
        assert mod.validate(feed) == []

    def test_bad_time_rejected(self, tmp_path):
        feed = tmp_path / "gtfs"
        _write_min_feed(feed, bad_time=True)
        mod = _load("validate_gtfs")
        problems = mod.validate(feed)
        assert any("bad arrival_time" in p for p in problems)

    def test_zip_feed(self, tmp_path):
        feed = tmp_path / "gtfs"
        _write_min_feed(feed)
        zpath = tmp_path / "feed.zip"
        with zipfile.ZipFile(zpath, "w") as zf:
            for p in feed.glob("*.txt"):
                zf.write(p, p.name)
        mod = _load("validate_gtfs")
        assert mod.validate(zpath) == []

    def test_cli_exit_one_on_invalid(self, tmp_path):
        feed = tmp_path / "gtfs"
        _write_min_feed(feed, missing="stops")
        cp = subprocess.run(
            [sys.executable, str(HOOKS_DIR / "validate_gtfs.py"), str(feed)],
            capture_output=True, text=True, timeout=30,
        )
        assert cp.returncode == 1
        assert "FAILED" in cp.stderr

    def test_time_parser(self):
        mod = _load("validate_gtfs")
        assert mod._parse_time("08:00:00")
        assert mod._parse_time("25:59:59")  # >24h ok
        assert mod._parse_time("")          # empty ok
        assert not mod._parse_time("8:00")
        assert not mod._parse_time("08:60:00")
        assert not mod._parse_time("notatime")


# --------------------------------------------------------------------------- #
# #9 check_data_fresh
# --------------------------------------------------------------------------- #
class TestCheckDataFresh:
    def _manifest(self, root: Path, end="20270101", downloaded=None):
        import datetime as dt
        (root / "data" / "raw").mkdir(parents=True, exist_ok=True)
        m = {
            "pvta_gtfs": {
                "downloaded": downloaded or dt.datetime.now().isoformat(timespec="seconds"),
                "validation": {"service_window": ["20260101", end]},
            }
        }
        (root / "data" / "raw" / "manifest.json").write_text(json.dumps(m))

    def test_missing_manifest_warns(self, tmp_path):
        mod = _load("check_data_fresh")
        warnings = mod.check(tmp_path)
        assert any("manifest missing" in w for w in warnings)

    def test_fresh_manifest_no_warnings(self, tmp_path):
        import datetime as dt
        end = (dt.date.today() + dt.timedelta(days=90)).strftime("%Y%m%d")
        self._manifest(tmp_path, end=end)
        mod = _load("check_data_fresh")
        assert mod.check(tmp_path) == []

    def test_stale_download_warns(self, tmp_path):
        import datetime as dt
        end = (dt.date.today() + dt.timedelta(days=90)).strftime("%Y%m%d")
        old = (dt.datetime.now() - dt.timedelta(days=30)).isoformat(timespec="seconds")
        self._manifest(tmp_path, end=end, downloaded=old)
        # also age the file mtime
        mf = tmp_path / "data" / "raw" / "manifest.json"
        old_ts = (dt.datetime.now() - dt.timedelta(days=30)).timestamp()
        os.utime(mf, (old_ts, old_ts))
        mod = _load("check_data_fresh")
        warnings = mod.check(tmp_path)
        assert any("days old" in w for w in warnings)

    def test_feed_end_within_14_days_warns(self, tmp_path):
        import datetime as dt
        soon = (dt.date.today() + dt.timedelta(days=5)).strftime("%Y%m%d")
        self._manifest(tmp_path, end=soon)
        mod = _load("check_data_fresh")
        warnings = mod.check(tmp_path)
        assert any("feed_end_date" in w for w in warnings)

    def test_always_exit_zero(self, tmp_path):
        cp = subprocess.run(
            [sys.executable, str(HOOKS_DIR / "check_data_fresh.py")],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "DATA_ROOT": str(tmp_path)},
        )
        assert cp.returncode == 0  # even with missing manifest


# --------------------------------------------------------------------------- #
# #10 update_traceability
# --------------------------------------------------------------------------- #
class TestUpdateTraceability:
    def _spec(self, root: Path, name: str, body: str):
        d = root / ".kiro" / "specs" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "requirements.md").write_text(body)

    def test_matrix_links_tests_and_flags_gaps(self, tmp_path):
        # Use fake ids (QZ-*, R91.1) that match the id grammar but collide with
        # no real spec id, so the REAL traceability run never credits a genuine
        # requirement to this test file.
        self._spec(tmp_path, "schedule-optimizer",
                   "- **QZ-1 (coverage).** THE optimizer SHALL score.\n"
                   "- **QZ-2 (never-worse).** suggested >= baseline.\n")
        self._spec(tmp_path, "manual-data",
                   "- **R91.1** loads clinics.\n")
        tdir = tmp_path / "tests" / "unit"
        tdir.mkdir(parents=True)
        (tdir / "test_opt.py").write_text(
            "def test_never_worse():\n    pass  # QZ-1 and QZ-2 covered\n")
        mod = _load("update_traceability")
        reqs, prose = mod.build_matrix(tmp_path)
        by_id = {r.rid: r for r in reqs}
        assert by_id["QZ-1"].refs and by_id["QZ-2"].refs
        assert by_id["R91.1"].refs == []  # gap: no test mentions R91.1
        md = mod.render(reqs, prose)
        assert "GAP" in md
        assert "`R91.1`" in md
        assert "QZ-1" in md

    def test_web_test_files_scanned(self, tmp_path):
        self._spec(tmp_path, "ui-week-grid-fake", "- **WQ-1** renders grid.\n")
        wdir = tmp_path / "web" / "src" / "components"
        wdir.mkdir(parents=True)
        (wdir / "Grid.test.tsx").write_text(
            "it('renders grid WQ-1', () => {});\n")
        mod = _load("update_traceability")
        reqs, _ = mod.build_matrix(tmp_path)
        wg1 = next(r for r in reqs if r.rid == "WQ-1")
        assert any("Grid.test.tsx" in ref for ref in wg1.refs)

    def test_prose_spec_reported(self, tmp_path):
        # a spec with no id tokens at all
        self._spec(tmp_path, "proseonly",
                   "The audit screen shows which clinic hours are reachable.\n")
        mod = _load("update_traceability")
        reqs, prose = mod.build_matrix(tmp_path)
        assert "proseonly" in prose

    def test_write_matrix_creates_file_and_cli_runs(self, tmp_path):
        self._spec(tmp_path, "s1", "- **QZ-9** at most k changes.\n")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "t.py").write_text("# QZ-9\n")
        mod = _load("update_traceability")
        out = mod.write_matrix(tmp_path)
        assert out.exists()
        assert "QZ-9" in out.read_text()
        # CLI path
        cp = subprocess.run(
            [sys.executable, str(HOOKS_DIR / "update_traceability.py")],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "TRACE_ROOT": str(tmp_path)},
        )
        assert cp.returncode == 0
        assert "wrote" in cp.stdout
