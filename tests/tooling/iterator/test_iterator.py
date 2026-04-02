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

@pytest.fixture
def cli_runner():
    return CliRunner()

@pytest.fixture
def mock_subprocess_run(monkeypatch):
    def _mock(stdout="OK", returncode=0):
        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args,
                returncode=returncode,
                stdout=stdout,
                stderr="",
            )
        monkeypatch.setattr(subprocess, "run", fake_run)
    return _mock

@pytest.fixture
def mock_cex(monkeypatch):
    fake = Mock(return_value={"signal": ["a", "b"]})
    monkeypatch.setattr("tooling.iterator.cex_iterator.pipeline", fake)
    return fake

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

def test_run_model_checker_success(tmp_path, monkeypatch, mock_subprocess_run):
    mock_subprocess_run(stdout="OK")
    it = Iterator(
        base_dir=tmp_path,
        iterations=1,
        single_timeout=1,
        global_timeout=1,
        smtlib_input=tmp_path / "file.smt2",
        debug=False,
        time_range="0:10",
        cycle_width=10,
        solver="yices",
        bmc_depth="10",
    )
    code, stdout, stderr = it.run_model_checker(tmp_path)
    assert code == 0
    assert stdout == "OK"

# run_iteration cases

def test_run_iteration_cex(tmp_path, monkeypatch, mock_cex):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="BMC failed\n",
            stderr="",
        )
    monkeypatch.setattr(subprocess, "run", fake_run)
    it = Iterator(
        tmp_path, 1, 1, 1, tmp_path / "f.smt2",
        False, "0:10", 10, "yices", "10"
    )
    result = it.run_iteration(0)
    assert result["status"] == "cex_created"
    mock_cex.assert_called_once()

def test_run_iteration_no_cex(tmp_path, monkeypatch):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="All good\n",
            stderr="",
        )
    monkeypatch.setattr(subprocess, "run", fake_run)
    it = Iterator(
        tmp_path, 1, 1, 1, tmp_path / "f.smt2",
        False, "0:10", 10, "yices", "10"
    )

    result = it.run_iteration(0)

    assert result["status"] == "no_cex"
    assert result["cex_changes"] is None


def test_run_iteration_timeout(tmp_path, monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="cmd", timeout=1)

    monkeypatch.setattr(subprocess, "run", fake_run)

    it = Iterator(
        tmp_path, 1, 1, 1, tmp_path / "f.smt2",
        False, "0:10", 10, "yices", "10"
    )

    result = it.run_iteration(0)

    assert result["status"] == "timeout"


def test_run_iteration_error(tmp_path, monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd="cmd")

    monkeypatch.setattr(subprocess, "run", fake_run)

    it = Iterator(
        tmp_path, 1, 1, 1, tmp_path / "f.smt2",
        False, "0:10", 10, "yices", "10"
    )

    result = it.run_iteration(0)

    assert result["status"] == "error"


# -------------------------
# run loop behavior
# -------------------------

def test_run_stops_on_timeout(tmp_path, monkeypatch):
    calls = []

    def fake_iteration(self, i):
        calls.append(i)
        return {"status": "timeout"}

    monkeypatch.setattr(Iterator, "run_iteration", fake_iteration)

    it = Iterator(
        tmp_path, 5, 1, 1, tmp_path / "f.smt2",
        False, "0:10", 10, "yices", "10"
    )

    it.run()

    assert len(calls) == 1  # stops early


def test_global_timeout(tmp_path, monkeypatch):
    def fake_iteration(self, i):
        return {"status": "no_cex"}

    monkeypatch.setattr(Iterator, "run_iteration", fake_iteration)

    it = Iterator(
        tmp_path, 5, 1, 0, tmp_path / "f.smt2",  # 0h timeout
        False, "0:10", 10, "yices", "10"
    )

    it.start_time = time.time() - 9999  # force timeout

    assert it.global_timeout_reached() is True


# -------------------------
# CLI tests
# -------------------------

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
