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

import builtins
from pathlib import Path
from collections import defaultdict
from unittest.mock import Mock

import pytest

from tooling.iterator.cex_iterator import (
    is_one,
    process_timeRange,
    print_changes,
    print_ids,
    post_process_vcd2smtc,
    smtlib2_constr_builder,
    smtlib2_constr_writer,
    smtlib2_constr_update,
    pipeline,
)

# is_one

@pytest.mark.parametrize(
    "input_str,expected",
    [
        ("1", True),
        ("01", True),
        ("001", True),
        ("0", False),
        ("", False),
        ("101", False),
        ("abc1", False),
        (" 001 ", True),
    ],
)
def test_is_one(input_str, expected):
    assert is_one(input_str) == expected

# process_timeRange

def test_process_timeRange():
    assert list(process_timeRange("1:3")) == [1, 2, 3]

def test_process_timeRange_single():
    assert list(process_timeRange("5")) == [5]

# print functions

def test_print_changes(capsys):
    data = [("sig", 10)]
    print_changes(data)

    captured = capsys.readouterr()
    assert "Signal:" in captured.out

def test_print_ids(capsys):
    ids = {0: ("sig", 5)}
    print_ids(ids)
    captured = capsys.readouterr()
    assert "Id:" in captured.out

# post_process_vcd2smtc

def test_post_process_vcd2smtc():
    raised = [
        ("top.sig1", 1),
        ("top.sig2", 1),
        ("top.sig3", 2),
    ]
    result = post_process_vcd2smtc(raised)
    assert result[1] == {"sig1", "sig2"}
    assert result[2] == {"sig3"}

# smtlib2_constr_builder

def test_smtlib2_constr_builder():
    data = {
        1: {"sig1", "sig2"},
    }
    result = smtlib2_constr_builder(data)
    assert "state 1\n" in result
    assert any("sig1" in r for r in result)
    assert any("sig2" in r for r in result)

# smtlib2_constr_writer

def test_smtlib2_constr_writer(tmp_path, capsys):
    file = tmp_path / "out.smtc"
    data = {1: {"sig1"}}
    smtlib2_constr_writer(data, file)
    assert file.exists()
    content = file.read_text()
    assert "state 1" in content
    assert "sig1" in content

# smtlib2_constr_update

def test_smtlib2_constr_update_new_file(tmp_path):
    file = tmp_path / "new.smtc"
    data = defaultdict(set, {1: {"sig1"}})

    smtlib2_constr_update(data, file)

    content = file.read_text()
    assert "state 1" in content
    assert "sig1" in content

def test_smtlib2_constr_update_existing(tmp_path):
    file = tmp_path / "existing.smtc"
    file.write_text(
        "state 1\n"
        "assume (= [sig1] false)\n"
    )
    data = defaultdict(set, {1: {"sig2"}})
    smtlib2_constr_update(data, file)
    content = file.read_text()
    # old + new signal should both exist
    assert "sig1" in content
    assert "sig2" in content

# pipeline (mocked parse_vcd)

def test_pipeline(monkeypatch, tmp_path):
    fake_parse = Mock(return_value=[
        ("top.sig1", 1),
        ("top.sig2", 2),
    ])
    monkeypatch.setattr("tooling.iterator.cex_iterator.parse_vcd", fake_parse)
    smtc_file = tmp_path / "out.smtc"
    raised, result = pipeline(
        vcd="file.vcd",
        pattern="_fault",
        time_range="0:10",
        cycle_w=10,
        smtc_file=smtc_file,
    )
    assert len(raised) == 2
    assert smtc_file.exists()
