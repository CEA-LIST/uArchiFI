# Copyright (C) 2026 Commissariat à l'énergie atomique et aux énergies
# alternatives (CEA)
#
# Licensed under the LGPL 2.1 license (the "License"); you may not use
# this file except in compliance with the License.
#
# You may obtain a copy of the License at :
# https://www.gnu.org/licenses/old-licenses/lgpl-2.1.fr.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied.
# See the License for the specific language governing permissions and 
# limitations under the License.

import json
import os
import signal
import subprocess
import time
from pathlib import Path
from unittest.mock import Mock
import pytest
from typer.testing import CliRunner

from tooling.iterator.runner import (
    Iterator,
    to_json_safe,
    save_results,
    app,
)

# Helpers

class FakeProc:
    """Minimal stand-in for subprocess.Popen."""

    def __init__(self, stdout="OK", stderr="", returncode=0, timeout=False, pid=4242):
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self._timeout = timeout
        self.pid = pid
        self.communicate_calls = 0

    def communicate(self, timeout=None):
        self.communicate_calls += 1
        # First call raises if we're simulating a hang; the post-kill call returns.
        if self._timeout and self.communicate_calls == 1:
            raise subprocess.TimeoutExpired(cmd="yosys-smtbmc", timeout=timeout)
        return self._stdout, self._stderr


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def fake_popen(monkeypatch):
    """Patch Popen; returns a dict holding the proc + captured cmd."""
    state = {}

    def _install(stdout="OK", stderr="", returncode=0, timeout=False):
        proc = FakeProc(stdout=stdout, stderr=stderr,
                        returncode=returncode, timeout=timeout)
        state["proc"] = proc

        def fake_popen(cmd, *args, **kwargs):
            state["cmd"] = cmd
            state["kwargs"] = kwargs
            return proc

        monkeypatch.setattr(subprocess, "Popen", fake_popen)
        return state

    return _install


@pytest.fixture
def fake_killpg(monkeypatch):
    """Record os.killpg calls instead of signalling a real process group."""
    calls = []
    monkeypatch.setattr(os, "killpg", lambda pid, sig: calls.append((pid, sig)))
    return calls


@pytest.fixture
def mock_cex(monkeypatch):
    fake = Mock(return_value={"signal": ["a", "b"]})
    monkeypatch.setattr("tooling.iterator.cex_iterator.pipeline", fake)
    return fake


def make_iterator(tmp_path, **overrides):
    kwargs = dict(
        base_dir=tmp_path,
        iterations=1,
        single_timeout=1,
        global_timeout=1,
        smtlib_input=tmp_path / "f.smt2",
        debug=False,
        time_range="0:10",
        cycle_width=10,
        solver="yices",
        bmc_depth="10",
    )
    kwargs.update(overrides)
    return Iterator(**kwargs)


# to_json_safe

def test_to_json_safe_basic():
    data = {
        "a": {1, 2},
        "b": (1, 2),
        "c": [{"x": 1}],
    }
    result = to_json_safe(data)
    assert isinstance(result["a"], list)
    assert result["b"] == [1, 2]
    assert result["c"][0]["x"] == 1


# save_results

def test_save_results(tmp_path):
    results = [{"iteration": 0, "status": "ok"}]

    save_results(results, tmp_path)

    output_file = tmp_path / "results.json"
    assert output_file.exists()

    content = json.loads(output_file.read_text())
    assert content[0]["status"] == "ok"


# Iterator.run_model_checker

def test_run_model_checker_success(tmp_path, fake_popen):
    state = fake_popen(stdout="OK")
    it = make_iterator(tmp_path)

    code, stdout, stderr = it.run_model_checker(tmp_path)

    assert code == 0
    assert stdout == "OK"
    assert state["proc"].communicate_calls == 1


def test_run_model_checker_uses_new_session(tmp_path, fake_popen):
    """Process group isolation is required for killpg to work."""
    state = fake_popen()
    it = make_iterator(tmp_path)

    it.run_model_checker(tmp_path)

    assert state["kwargs"].get("start_new_session") is True


def test_run_model_checker_passes_single_timeout(tmp_path, monkeypatch):
    seen = {}

    class RecordingProc(FakeProc):
        def communicate(self, timeout=None):
            seen["timeout"] = timeout
            return super().communicate(timeout=timeout)

    monkeypatch.setattr(subprocess, "Popen",
                        lambda *a, **k: RecordingProc())
    it = make_iterator(tmp_path, single_timeout=3)

    it.run_model_checker(tmp_path)

    assert seen["timeout"] == 3 * 60  # minutes -> seconds


def test_run_model_checker_timeout_kills_process_group(tmp_path, fake_popen, fake_killpg):
    state = fake_popen(stdout="partial", stderr="boom", timeout=True)
    it = make_iterator(tmp_path)

    with pytest.raises(subprocess.TimeoutExpired) as excinfo:
        it.run_model_checker(tmp_path)

    # The group was killed exactly once, with SIGKILL, on the child's pid.
    assert fake_killpg == [(state["proc"].pid, signal.SIGKILL)]
    # Output was still drained after the kill and attached to the exception.
    assert state["proc"].communicate_calls == 2
    assert excinfo.value.stdout == "partial"
    assert excinfo.value.stderr == "boom"


def test_run_model_checker_no_kill_on_success(tmp_path, fake_popen, fake_killpg):
    fake_popen(stdout="OK")
    it = make_iterator(tmp_path)

    it.run_model_checker(tmp_path)

    assert fake_killpg == []


# run_iteration cases

def test_run_iteration_cex(tmp_path, fake_popen, mock_cex):
    fake_popen(stdout="BMC failed\n")
    it = make_iterator(tmp_path)

    result = it.run_iteration(0)

    assert result["status"] == "cex_created"
    mock_cex.assert_called_once()


def test_run_iteration_no_cex(tmp_path, fake_popen):
    fake_popen(stdout="All good\n")
    it = make_iterator(tmp_path)

    result = it.run_iteration(0)

    assert result["status"] == "no_cex"
    assert result["cex_changes"] is None


def test_run_iteration_timeout(tmp_path, fake_popen, fake_killpg):
    state = fake_popen(timeout=True)
    it = make_iterator(tmp_path)

    result = it.run_iteration(0)

    assert result["status"] == "timeout"
    assert result["cex_changes"] is None
    # The hung model checker must not be left running.
    assert fake_killpg == [(state["proc"].pid, signal.SIGKILL)]


def test_run_iteration_error(tmp_path, monkeypatch):
    def fake_popen(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd="cmd")

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    it = make_iterator(tmp_path)

    result = it.run_iteration(0)

    assert result["status"] == "error"


# run loop behavior

def test_run_stops_on_timeout(tmp_path, monkeypatch):
    calls = []

    def fake_iteration(self, i):
        calls.append(i)
        return {"status": "timeout"}

    monkeypatch.setattr(Iterator, "run_iteration", fake_iteration)

    it = make_iterator(tmp_path, iterations=5)
    it.run()

    assert len(calls) == 1  # stops early


def test_global_timeout(tmp_path, monkeypatch):
    def fake_iteration(self, i):
        return {"status": "no_cex"}

    monkeypatch.setattr(Iterator, "run_iteration", fake_iteration)

    it = make_iterator(tmp_path, iterations=5, global_timeout=0)
    it.start_time = time.time() - 9999  # force timeout

    assert it.global_timeout_reached() is True


# CLI tests

def test_cli_runs(tmp_path, cli_runner, monkeypatch):
    def fake_run(self):
        return None

    monkeypatch.setattr(Iterator, "run", fake_run)

    result = cli_runner.invoke(
        app,
        [
            str(tmp_path),
            str(tmp_path / "file.smt2"),
            "1",
            "0:10",
            "10",
        ],
    )

    assert result.exit_code == 0


def test_cli_invalid_args(cli_runner):
    result = cli_runner.invoke(app, [])

    assert result.exit_code != 0
