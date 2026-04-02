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

import tempfile
import os
import pytest
from tooling.iterator import cex_iterator

# Helpers

def write_temp_vcd(content):
    tmp = tempfile.NamedTemporaryFile(delete=False, mode="w")
    tmp.write(content)
    tmp.close()
    return tmp.name

def dummy_time_range(x):
    # Return cycles 0–2000
    return set(range(0, 2000))

def dummy_is_one(val):
    # Define "logical 1" as:
    # - scalar 1
    # - vector with any '1'
    return any(c == "1" for c in val)

# Monkeypatch helpers
@pytest.fixture(autouse=True)
def patch_helpers(monkeypatch):
    monkeypatch.setattr(cex_iterator, "is_one", dummy_is_one)

# process_timeRange tests

def test_time_range_single():
    assert list(cex_iterator.process_timeRange("10")) == [10]

def test_time_range_range():
    assert list(cex_iterator.process_timeRange("10:12")) == [10, 11, 12]

# Full Comprehensive Test

def test_all_vcd_keywords():

    vcd = """\
$comment Test VCD $end
$date today $end
$version 1.0 $end
$timescale 10 ps $end

$scope module top $end
$scope fork inner $end
$var wire 1 ! a_scalar $end
$var reg 1 & a_reg $end
$var integer 8 " b_vector $end
$upscope $end

$var real 64 # c_real $end
$var string 1 $ d_string $end
$var parameter 1 % p_param $end
$upscope $end

$enddefinitions $end

#0
$dumpvars
1!
1&
b1010 "
r12.34 #
shello $
1%
$end

#10
0!
#20
b1zzz "
#30
r1e-10 #
#40
sbye $

$comment
multiline
comment
$end
"""

    path = write_temp_vcd(vcd)
    results = cex_iterator.parse_vcd(
        input_file=path,
        signal_pattern="",
        time_range_input="0:2000",
        cycle_w=1
    )
    os.remove(path)
    # Expected signals raised (value considered logical 1)
    expected_signals = {
        "top.inner.a_scalar",
        "top.inner.a_reg",
        "top.inner.b_vector",
        "top.c_real",
        "top.d_string",
        "top.p_param"
    }
    returned_signals = {sig for sig, _ in results}
    assert expected_signals.issubset(returned_signals)

# Test Scope Nesting

def test_scope_hierarchy():

    vcd = """\
$scope module A $end
$scope module B $end
$var wire 1 ! sig $end
$upscope $end
$upscope $end
$enddefinitions $end
#0
1!
"""

    path = write_temp_vcd(vcd)
    results = cex_iterator.parse_vcd(
        input_file=path,
        signal_pattern="sig",
        time_range_input="0:10",
        cycle_w=1
    )
    os.remove(path)
    assert ("A.B.sig", 0) in results

# Test Scalar Formats

def test_scalar_formats():

    vcd = """\
$scope module T $end
$var wire 1 ! s $end
$upscope $end
$enddefinitions $end
#0
1!
#1
0!
#2
x!
#3
z!
"""

    path = write_temp_vcd(vcd)
    results = cex_iterator.parse_vcd(
        input_file=path,
        signal_pattern="s",
        time_range_input="0:10",
        cycle_w=1
    )
    os.remove(path)
    # Only time 0 should count
    assert ("T.s", 0) in results
    assert not any(t == 1 for _, t in results)

# Test Vector Formats

def test_vector_formats():

    vcd = """\
$scope module T $end
$var wire 4 ! v $end
$upscope $end
$enddefinitions $end
#0
b0000 !
#1
b1000 !
"""
    path = write_temp_vcd(vcd)
    results = cex_iterator.parse_vcd(
        input_file=path,
        signal_pattern="v",
        time_range_input="0:10",
        cycle_w=1
    )
    os.remove(path)
    assert ("T.v", 1) in results
    assert not any(t == 0 for _, t in results)

# Test Real Formats

def test_real_formats():

    vcd = """\
$scope module T $end
$var real 64 ! r $end
$upscope $end
$enddefinitions $end
#0
r0.0 !
#1
r3.14 !
"""

    path = write_temp_vcd(vcd)
    results = cex_iterator.parse_vcd(
        input_file=path,
        signal_pattern="r",
        time_range_input="0:10",
        cycle_w=1
    )
    os.remove(path)
    assert ("T.r", 1) in results
    assert not any(t == 0 for _, t in results)

# Test String Formats

def test_string_formats():

    vcd = """\
$scope module T $end
$var string 1 ! s $end
$upscope $end
$enddefinitions $end
#0
s !
#1
shello !
"""

    path = write_temp_vcd(vcd)
    results = cex_iterator.parse_vcd(
        input_file=path,
        signal_pattern="s",
        time_range_input="0:10",
        cycle_w=1
    )
    os.remove(path)
    assert ("T.s", 1) in results
    assert not any(t == 0 for _, t in results)
