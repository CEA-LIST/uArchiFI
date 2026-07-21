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

import subprocess
import time
import os
import re
import pty
import sys
import json
import signal
from pathlib import Path
from collections import defaultdict
from tooling.iterator import cex_iterator as cex
from typing import Annotated

import typer
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table

app = typer.Typer()
console = Console()

DEFAULT_TIMEOUT = 60
DEFAULT_GLOBAL_TIMEOUT = 4
DEFAULT_ITER = 2
DEFAULT_SOLVER = "yices"

# Dictionary reformatter helper
def to_json_safe(obj):
    if isinstance(obj, defaultdict):
        return {k: to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, dict):
        return {k: to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, tuple):
        return [to_json_safe(v) for v in obj]
    if isinstance(obj, list):
        return [to_json_safe(v) for v in obj]
    return obj

def save_results(results, base_dir):
    res_file = base_dir / "results.json"
    with open(res_file, "w") as f:
        json.dump(to_json_safe(results), f, indent=2)
    console.print(f"[green]Results saved in:[/green] {res_file}")

def validate_time_range(value: str) -> str:
    """
    Valid formats:
    - "10"
    - "10:20"
    """
    # Match "10" or "10:20"
    pattern = r"^\d+$|^\d+:\d+$"
    if not re.match(pattern, value):
        raise typer.BadParameter(
            "Invalid time range format. Use 'N' or 'start:end' (e.g. 10 or 10:20)"
        )
    if ":" in value:
        start, end = map(int, value.split(":"))
        if start > end:
            raise typer.BadParameter("Start must be <= end in time range")

    return value

# Core
class Iterator:

    def __init__(
        self,
        base_dir,
        iterations,
        single_timeout,
        global_timeout,
        smtlib_input,
        debug,
        time_range,
        cycle_width,
        solver,
        bmc_depth,
    ):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.iterations = iterations
        self.single_timeout = single_timeout*60 #Minutes
        self.global_timeout = global_timeout*60*60 #Hours
        self.smt2_file = Path(smtlib_input)
        self.debug = debug

        self.time_range = time_range
        self.cycle_width = cycle_width
        self.solver = solver
        self.bmc_depth = bmc_depth

        self.constr_file = self.base_dir / "constr.smtc"
        self.constr_file.touch(exist_ok=True)

        self.results = []
        self.start_time = None

    # Global Timeout
    def global_timeout_reached(self):
        elapsed = time.time() - self.start_time
        return elapsed >= self.global_timeout

    # Model Checker
    def run_model_checker(self, run_folder):

        cmd = [
                "yosys-smtbmc",
                "-t",str(self.bmc_depth),
                "-s", self.solver,
                "--presat",
                "--dump-vcd", str(run_folder / "cex.vcd"),
                "--smtc", str(self.constr_file),
                str(self.smt2_file),
        ]

        if self.debug:
            console.print("[yellow]Debug mode: streaming output[/yellow]")
            console.print(f"Running :{' '.join(cmd)}") 
            master_fd, slave_fd = pty.openpty() #Mirror pty because yosys-smtbmc 
            process = subprocess.Popen(         #needs it for live update and live timer
                cmd,
                stdout=slave_fd,
                stderr=slave_fd,
                text=True,
                close_fds=True,
            )
            os.close(slave_fd)
            std_out_chunks = []
            try:
                while True:
                    try:
                        data = os.read(master_fd, 1024).decode('utf-8')
                        if not data:
                            break
                        sys.stdout.write(data)
                        sys.stdout.flush()

                        std_out_chunks.append(data)
                    except OSError:
                        break
            finally:
                process.wait()
                os.close(master_fd)
            fullout = "".join(std_out_chunks)
            return process.returncode, fullout, ""
        else:
            with Live(Spinner("dots", text="Model checker running..."), console=console):
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    start_new_session=True,
                )

                try:
                    stdout, stderr = proc.communicate(timeout=self.single_timeout)
                    return proc.returncode, stdout, stderr

                except subprocess.TimeoutExpired as e:
                    # kill the whole process group
                    os.killpg(proc.pid, signal.SIGKILL)
                    stdout, stderr = proc.communicate()
                    e.stderr = stderr
                    e.stdout = stdout
                    
                    raise
             #   result = subprocess.run(
             #       cmd,
             #       capture_output=True,
             #       timeout=self.single_timeout,
             #       text=True,
             #       preexec_fn=os.setsid,
             #   )
            #return result.returncode, result.stdout, result.stderr

    # Log
    def write_log(self, run_folder, stdout, stderr):
        log_file = run_folder / "model_checker.log"
        with open(log_file, "w") as f:
            f.write("-- stdout --\n")
            f.write(stdout)
            f.write("\n-- stderr --\n")
            f.write(stderr)

    # CEX Processing
    def process_cex(self, iteration, run_folder):
        console.print(f"[green]CEX found at iteration {iteration}[/green]")
        signals = cex.pipeline( run_folder / "cex.vcd", 
                               "_fault_sel",
                               self.time_range,
                               self.cycle_width,
                               self.constr_file
                               )
        with open(run_folder / "cex_signals.json", "w") as f:
            json.dump(to_json_safe(signals), f, indent=2)
        return {
            "iteration": iteration,
            "status": "cex_created",
            "cex_changes": signals,
        }

    # Single Iteration
    def run_iteration(self, i):
        run_folder = self.base_dir / f"iter_{i}"
        run_folder.mkdir(parents=True, exist_ok=True)
        console.print(f"[cyan]Starting iteration {i}[/cyan]")
        start = time.time()
        try:
            code, stdout, stderr = self.run_model_checker(run_folder)
            if not self.debug:
                self.write_log(run_folder, stdout, stderr)
            if "BMC failed" in stdout:
                res = self.process_cex(i, run_folder)
            else:
                res = {
                    "iteration": i,
                    "status": "no_cex",
                    "cex_changes": None,
                }
        except subprocess.TimeoutExpired:
            res = {
                "iteration": i,
                "status": "timeout",
                "cex_changes": None,
            }
        except subprocess.CalledProcessError as e:
            res = {
                "iteration": i,
                "status": "error",
                "cex_changes": str(e),
            }
        duration = time.time() - start
        res["duration_sec"] = round(duration, 2)
        console.print(f"[blue]Iteration {i} done in {duration:.2f}s[/blue]")
        return res

    # Looper
    def run(self):
        self.start_time = time.time()
        for i in range(self.iterations):

            if self.global_timeout_reached():
                console.print("[red]Global timeout reached[/red]")
                break
            result = self.run_iteration(i)
            self.results.append(result)
            if result["status"] == "no_cex":
                console.print(f"[yellow]>> No cex found for iter {i}: stopping[/yellow]")
                break
            if result["status"] == "timeout":
                console.print("[yellow]>>Stopping due to timeout[/yellow]")
                break

        save_results(self.results, self.base_dir)

# CLI
@app.command()

def main(
    base_dir: Annotated[
        str,
        typer.Argument(help="Folder for outputs")
    ],
    smtlib_input: Annotated[
        str,
        typer.Argument(help="SMTLIB_v2 input file for yosys-smtbmc solver")
    ],
    iterations: Annotated[
        int,
        typer.Argument(min=1,help="Number of iterations to run the model checker")
    ],
    time_range: Annotated[
        str,
        typer.Argument(help="Time range where faults are injected (e.g. 0:10)",
                       callback=validate_time_range
        )
    ],
    bmc_depth: Annotated[
        int,
        typer.Argument(min=1,help="Bounded Model Checking Depth for solver")
    ],

    # Optionals
    run_timeout: Annotated[
        int,
        typer.Option("--run-time",min=1, help="Timeout for a single iteration (minutes)")
    ] = DEFAULT_TIMEOUT,
    global_timeout: Annotated[
        int,
        typer.Option("--glob-time",min=1, help="Global timeout across all iterations (hours)")
    ] = DEFAULT_GLOBAL_TIMEOUT,
    debug: Annotated[
        bool,
        typer.Option("--debug", "-d", help="Enable live streaming output from model checker")
    ] = False,
    cycle_width: Annotated[
        int,
        typer.Option(help="Cycle width in VCD CEX files (yosys-smtbmc default = 10)")
    ] = 10,
    solver: Annotated[
        str,
        typer.Option("--solver", "-s", help="Solver for yosys-smtbmc (default: yices)")
    ] = DEFAULT_SOLVER,
):
    """Run model checker iterator with CEX extraction"""

    table = Table(title="Configuration")
    table.add_column("Param")
    table.add_column("Value")
    table.add_row("Base Dir", base_dir)
    table.add_row("Input File", smtlib_input)
    table.add_row("Iterations", str(iterations))
    table.add_row("Run Timeout", str(run_timeout))
    table.add_row("Global Timeout", str(global_timeout))
    table.add_row("Solver", str(solver))
    table.add_row("BMC Depth", str(bmc_depth))

    console.print(table)

    iterator = Iterator(
        base_dir,
        iterations,
        run_timeout,
        global_timeout,
        smtlib_input,
        debug,
        time_range,
        cycle_width,
        solver,
        bmc_depth,
    )

    iterator.run()

if __name__ == "__main__":
    app()
