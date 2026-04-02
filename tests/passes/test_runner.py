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

import pathlib
import subprocess
import shutil
import difflib
import os
import pytest

YOSYS = os.environ.get("YOSYS", "yosys")

BASE_DIR = pathlib.Path(__file__).resolve().parent
TEST_ROOT = BASE_DIR / "tests"


def find_testdirs():
    tests_list = []
    for p in TEST_ROOT.rglob("test.tcl"):
        tmp = p.parent.resolve()
        tests_list.append(tmp)
    return sorted(tests_list)

def parse_meta(meta_path):
    if not meta_path.exists():
        return None, "yosys"

    supported_versions = None
    compare_mode = "yosys"   # default

    for line in meta_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("supported_versions"):
            _, value = line.split("=", 1)
            supported_versions = [v.strip() for v in value.split(",")]

        if line.startswith("compare"):
            _, value = line.split("=", 1)
            compare_mode = value.strip()

    return supported_versions, compare_mode

def resolve_golden_file(testdir, base_name, variant):
    """
    Resolution order:
        golden_<variant>.<ext>
        golden.<ext>
    """

    base_path = pathlib.Path(base_name)
    stem = base_path.stem        # "golden"
    suffix = base_path.suffix    # ".txt" or ".rtlil"

    versioned = testdir / f"{stem}_{variant}{suffix}"
    default = testdir / base_name

    if versioned.exists():
        return versioned

    if default.exists():
        return default

    return None


TESTDIRS = find_testdirs()


@pytest.mark.parametrize(
    "testdir",
    TESTDIRS,
    ids=[str(p.relative_to(TEST_ROOT)) for p in TESTDIRS],
)
def test_yosys_directory(testdir, yosys_variant):
    testdir = pathlib.Path(testdir)

    meta_file = testdir / "test.meta"
    supported_versions, compare_mode = parse_meta(meta_file)

    # Version filtering

    if supported_versions is not None:
        if yosys_variant not in supported_versions:
            pytest.skip(
                f"Not supported for yosys {yosys_variant} "
                f"(supports {supported_versions})"
            )

    print(f"\nRunning {testdir} with YOSYS_VARIANT={yosys_variant}")

    # Cleanup

    for name in ["status", "result.log", "yosys_stdout.log"]:
        f = testdir / name
        if f.exists():
            f.unlink()

    # Run Yosys

    env = os.environ.copy()
    env["YOSYS_VARIANT"] = yosys_variant

    proc = subprocess.run(
        [YOSYS, "-c", "test.tcl"],
        cwd=testdir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    stdout_file = testdir / "yosys_stdout.log"
    stdout_file.write_text(proc.stdout)
    shutil.copy(stdout_file, testdir / "result.log")

    # Versioned golden

    golden_txt = resolve_golden_file(
        testdir, "golden.txt", yosys_variant
    )

    # Retunr of exec invocation

    golden_rtlil = resolve_golden_file(
        testdir, "golden.rtlil", yosys_variant
    )

    result_rtlil = testdir / "result.rtlil"

    # String-based test
    if golden_txt is not None:

        if compare_mode == "exec":
            exec_output_file = testdir / "exec_output.txt"

            if not exec_output_file.exists():
                pytest.fail(
                    f"{testdir}: exec_output.txt not produced",
                    pytrace=False
                )

            actual_output = exec_output_file.read_text().strip()
        else:
            actual_output = proc.stdout.strip()

        expected_string = golden_txt.read_text().strip()

        if expected_string not in actual_output:
            pytest.fail(
                f"{testdir}: string mismatch "
                f"(using {golden_txt.name})",
                pytrace=False
            )

        return

    # RTLIL-based test

    if golden_rtlil is not None:
        if not result_rtlil.exists():
            pytest.fail(f"{testdir}: no result.rtlil produced")

        golden_lines = golden_rtlil.read_text().splitlines()[1:]
        result_lines = result_rtlil.read_text().splitlines()[1:]

        if golden_lines != result_lines:
            diff = "\n".join(
                difflib.unified_diff(
                    golden_lines,
                    result_lines,
                    fromfile=golden_rtlil.name,
                    tofile="result.rtlil",
                )
            )
            pytest.fail(
                f"{testdir}: RTLIL mismatch "
                f"(using {golden_rtlil.name})\n{diff}"
            )

        return

    pytest.skip("No golden file found")
