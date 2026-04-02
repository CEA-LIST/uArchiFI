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

import re
from collections import defaultdict

def is_one(bitstring: str) -> bool:
    # Strip optional whitespace
    s = bitstring.strip()
    return len(s) > 0 and s.endswith("1") and set(s[:-1]) <= {"0"}

def process_timeRange(time_range_input: str):
    if ":" in time_range_input:
        start, end = map(int, time_range_input.split(":"))
        return range(start, end + 1)
    else:
        value = int(time_range_input)
        return range(value, value +1)

def parse_vcd(input_file, signal_pattern, time_range_input, cycle_w):
    """
    VCD parser supporting:
    - All standard VCD header keywords
    - All $var types
    - All scope types
    - Scalar, vector, real and string value changes
    - $dumpvars, $dumpon, $dumpoff, $dumpall
    - Multi-line $comment blocks
    """

    good_signals = {}
    raised_list = []
    scope_stack = []

    current_time = 0
    start_time_segment = False
    in_definitions = True
    in_comment_block = False
    in_dump_section = False

    time_range = process_timeRange(time_range_input)

    def in_time_window(time_raw):
        cycle = int(int(time_raw) / int(cycle_w))
        return cycle in time_range, cycle

    with open(input_file, "r") as f:
        for raw_line in f:
            line = raw_line.strip()

            if not line:
                continue

            # Handle multi-line $comment blocks
            if in_comment_block:
                if "$end" in line:
                    in_comment_block = False
                continue

            if line.startswith("$comment"):
                if not line.endswith("$end"):
                    in_comment_block = True
                continue

            # HEADER SECTION
            if in_definitions:

                if line.startswith("$date") or \
                   line.startswith("$version") or \
                   line.startswith("$timescale"):
                    continue

                if line.startswith("$scope"):
                    # $scope module alpha $end
                    parts = line.split()
                    if len(parts) >= 3:
                        scope_stack.append(parts[2])
                    continue

                if line.startswith("$upscope"):
                    if scope_stack:
                        scope_stack.pop()
                    continue

                if line.startswith("$var"):
                    # $var wire 1 ! a_scalar $end
                    parts = line.split()
                    if len(parts) >= 5:
                        var_type = parts[1]          # wire, reg, integer, real, string
                        var_width = parts[2]
                        vcd_id = parts[3]
                        signal_name = parts[4]

                        full_signal_name = ".".join(scope_stack + [signal_name])

                        if signal_pattern in signal_name:
                            good_signals[vcd_id] = full_signal_name
                    continue

                if line.startswith("$enddefinitions"):
                    in_definitions = False
                    continue

                continue  # Skip anything else in header

            # TIME CHANGE
            if line.startswith("#"):
                raw_time = line[1:]
                is_valid, cycle = in_time_window(raw_time)
                start_time_segment = is_valid
                current_time = cycle
                continue

            # Dump control keywords
            if line.startswith("$dumpvars"):
                in_dump_section = True
                continue

            if line.startswith("$dumpon") or \
               line.startswith("$dumpoff") or \
               line.startswith("$dumpall"):
                continue

            if line.startswith("$end"):
                in_dump_section = False
                continue

            # Skip if not in relevant time window
            if not start_time_segment:
                continue

            # VALUE CHANGES

            # Scalar change: 1! 0! x! z!
            if re.match(r"^[01xzXZ].+", line):
                value = line[0]
                vcd_id = line[1:]

                if vcd_id in good_signals:
                    if value == "1":
                        raised_list.append(
                            (good_signals[vcd_id], current_time)
                        )
                continue

            # Vector change: b1010 
            if line.startswith("b"):
                parts = line.split()
                if len(parts) == 2:
                    value = parts[0][1:]
                    vcd_id = parts[1]

                    if vcd_id in good_signals:
                        if is_one(value):
                            raised_list.append(
                                (good_signals[vcd_id], current_time)
                            )
                continue

            # Real change: r12.34 
            if line.startswith("r"):
                parts = line.split()
                if len(parts) == 2:
                    value = parts[0][1:]
                    vcd_id = parts[1]

                    if vcd_id in good_signals:
                        try:
                            if float(value) != 0.0:
                                raised_list.append(
                                    (good_signals[vcd_id], current_time)
                                )
                        except ValueError:
                            pass
                continue

            #String change: shello $
            if line.startswith("s"):
                parts = line.split()
                if len(parts) == 2:
                    value = parts[0][1:]
                    vcd_id = parts[1]

                    if vcd_id in good_signals:
                        if value:  # non-empty string
                            raised_list.append(
                                (good_signals[vcd_id], current_time)
                            )
                continue

    return raised_list

def print_changes(input_list):
    for i in input_list:
        print("Signal: ", i[0], " raised @ ", i[1], "\n")
    return

def print_ids(ids_list):
    for index, key in enumerate(ids_list):
        signal, tick = ids_list[key]
        print(f"Id: {key} | Signal: {signal} | @ tick {tick}")
    return

def post_process_vcd2smtc(raised_list):
    """
        Post-process the vcd parser result to prepare for smtc constraints builder
    """
    result = defaultdict(set) #Dict of lists of signals
    for signal in raised_list:
        sig_no_top = ".".join(signal[0].split(".",1)[1:]) #Strips top module off signal name
        result[signal[1]].add(sig_no_top)
    return result

def smtlib2_constr_builder(constr_dict):
    """
        Takes as input a dictionary of lists fault_sel activated on each tick time with the tick times,
        then builds a list of smtlib2 constraints to exclude those signals 
        being activated @tick<X> with assume constraints
    """
    results = []
    pattern_step = "state {tick}\n"
    pattern = "assume (= [{sig_name}] false)\n"
    for index,key in enumerate(constr_dict): #TODO refactor with sorted values
        results.append(pattern_step.format(tick=key))
        for sig in constr_dict[key]:
            results.append(pattern.format(sig_name=sig)) 
    return results

def smtlib2_constr_writer(input_dict, smtc_out_file):
    section_list = smtlib2_constr_builder(input_dict)
    with open(smtc_out_file, "w") as f:
        print("--- Adding constr to smtc file : ---\n")
        for item in section_list:
            print(item)
            f.write(item)
    return

def smtlib2_constr_update(input_dict, smtc_out_file):
    """
        Updates the provided .smtc file :
        - Adds new 'assume' statements in the corresponding time slots
        - If the state section is not present it creates one if is present it
        appends the new assume at the end of the section
    """
    #Use the already build dict and parse the whole file then add the assumes in the right id
    current_state = 0
    try:
        with open(smtc_out_file, "r") as f: 
            for line in f:
                line.strip()
                line = line.split(" ")
                if line[0] == "state":
                    current_state = int(line[1])
                    continue
                if line[0] == "assume":
                    input_dict[current_state].add(line[2][1:-1])
                    continue
                else:
                    continue
            smtlib2_constr_writer(input_dict,smtc_out_file)
            return
    except FileNotFoundError:
        print("File not found => writing to new file")
        smtlib2_constr_writer(input_dict,smtc_out_file)
        return

def pipeline(vcd, pattern, time_range, cycle_w, smtc_file):
    print(f"Running with: {vcd}, {pattern}, {time_range}, {cycle_w}, {smtc_file}")
    raised_list  = parse_vcd(vcd, pattern, time_range, cycle_w)
    print(f"Fault selectors raised : ")
    print_changes(raised_list)
    signals = post_process_vcd2smtc(raised_list)
    constr_added = smtlib2_constr_update(signals, smtc_file)
    return raised_list, constr_added

if __name__ == "__main__":
    main()
