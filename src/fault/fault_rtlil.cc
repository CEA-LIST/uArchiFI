/*
 *  Fault RTLIL -- Fault injection pass
 *
 *  Copyright (C) 2023 Commissariat à l'énergie atomique et aux énergies
 *  alternatives (CEA)
 *
 *  Permission to use, copy, modify, and/or distribute this software for any
 *  purpose with or without fee is hereby granted, provided that the above
 *  copyright notice and this permission notice appear in all copies.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 *  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 *  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 *  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 *  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 *  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 */

#include "kernel/ff.h"
#include "kernel/ffinit.h"
#include "kernel/sigtools.h"
#include "kernel/yosys.h"

#define CNT_WIDTH 8
#define CLK_WIDTH 32

USING_YOSYS_NAMESPACE
PRIVATE_NAMESPACE_BEGIN

struct FaultRTLILPass : public Pass {
	FaultRTLILPass() : Pass("fault_rtlil", "insert mux in circuit to emulate faults") {}
	void help() override
	{
		//   |---v---|---v---|---v---|---v---|---v---|---v---|---v---|---v---|---v---|---v---|
		log("\n");
		log("    fault_rtlil [options]\n");
		log("\n");
		log("This command emulates faults on wires in the current selection (see 'help select').\n");
		log("This pass is intended to be used with a formal verification backend to perform\n");
		log("model checking (see 'help write_smt2' or 'help write_btor').\n");
		log("\n");
		log("    -permanent\n");
		log("        Inject a fault that permanently affects the circuit.\n");
		log("        This option is not compatible with 'timing' and 'cnt' options.\n");
		log("        If unspecified, the injected fault will be transient by default.\n");
		log("\n");
		log("    -timing <range>\n");
		log("        Specify the timing in which the transient fault can be performed.\n");
		log("        <range> is a colon-separated range, e.g., 10:20, or a single step, e.g., 14.\n");
		log("        The fault cannot be injected before or after the specified timing range.\n");
		log("        The design needs to be flattened to create a clock to control the timing.\n");
		log("        If unspecified, the fault can be injected at any step of the verification.\n");
		log("\n");
		log("    -effect { set | reset | flip | diff | fixed <value> }\n");
		log("        Constrain the fault value. If unspecified, an arbitrary fault is injected\n");
		log("        in the location. This means that the fault can take every possible value.\n");
		log("\n");
		log("        set\n");
		log("            Set all bits of the target to one.\n");
		log("\n");
		log("        reset\n");
		log("            Set all bits of the target to zero.\n");
		log("\n");
		log("        flip\n");
		log("            Flip all bits of the target.\n");
		log("\n");
		log("        diff\n");
		log("            Set the fault to a different value that the correct one.\n");
		log("\n");
		log("        fixed <value>\n");
		log("            Set the fault to the specified value.\n");
		log("\n");
		log("    -cnt [ local ] <max_fault>\n");
		log("        A global counter is generated to count the number of faults injected.\n");
		log("        The design needs to be flattened before creating the global counter.\n");
		log("        <max_fault> specifies the maximum number of faults that can be inserted\n");
		log("        in the design. Options can be used to add constraints on the counter.\n");
		log("\n");
		log("        local\n");
		log("            A counter is locally generated for each targeted location. This does\n");
		log("            not require flattening the design.\n");
		log("\n");
	}
	void execute(std::vector<std::string> args, Design *design) override
	{
		bool permanent = false;
		bool timing = false;
		int timing_lbound = -1, timing_ubound = -1;
		typedef enum effect { SYMBOLIC, SET, RESET, FLIP, FIXED, DIFF } effect_t;
		int effect_value = -1;
		effect_t effect = SYMBOLIC;
		bool insert_cnt = false;
		bool local_cnt = false;
		int cnt_bound = -1;

		log_header(design, "Executing FaultRTLIL pass.\n");

		// log_push();
		// Pass::call(design, "hierarchy -check");
		// log_pop();

		size_t argidx;
		for (argidx = 1; argidx < args.size(); argidx++) {
			if (args[argidx] == "-permanent") {
				if (insert_cnt || timing) {
					log_error("fault_rtlil 'permanent' option is not compatible with 'timing' and 'cnt' options.\n");
				}
				permanent = true;
				continue;
			}
			if (args[argidx] == "-timing" && argidx + 1 < args.size()) {
				if (permanent) {
					log_error("fault_rtlil 'permanent' option is not compatible with 'timing' and 'cnt' options.\n");
				}
				timing = true;
				std::string timing_arg = args[++argidx];
				size_t found = timing_arg.find(':');
				if (found == std::string::npos) {
					timing_lbound = timing_ubound = stoi(timing_arg);
				} else {
					timing_lbound = stoi(timing_arg.substr(0, found));
					timing_ubound = stoi(timing_arg.substr(found + 1));
				}
				continue;
			}
			if (args[argidx] == "-effect" && argidx + 1 < args.size()) {
				std::string effect_arg = args[++argidx];
				std::cout << effect_arg << std::endl;
				if (effect_arg == "set") {
					effect = SET;
				} else if (effect_arg == "reset") {
					effect = RESET;
				} else if (effect_arg == "flip") {
					effect = FLIP;
				} else if (effect_arg == "diff") {
					effect = DIFF;
				} else if (effect_arg == "fixed") {
					if (argidx + 1 == args.size())
						log_warning("Unspecified value for 'fault_rtlil -effect fixed'\n");
					effect = FIXED;
					effect_value = stoi(args[++argidx]);
				} else {
					log_warning("Unrecognize option with the -effect flag\n");
				}
				continue;
			}
			if (args[argidx] == "-cnt" && argidx + 1 < args.size()) {
				if (permanent) {
					log_error("fault_rtlil 'permanent' option is not compatible with 'timing' and 'cnt' options.\n");
				}
				insert_cnt = true;
				if (args[argidx + 1] == "local" && argidx + 2 < args.size()) {
					local_cnt = true;
					argidx++;
				}
				cnt_bound = stoi(args[++argidx]);
				continue;
			}
			log_error("Unknown flag '%s' given to FaultRTLIL.\n", args[argidx].c_str());
			break;
		}
		// extra_args(args, argidx, design);

		if (GetSize(design->selected_modules()) == 0) {
			log_warning("Can't operate on an empty selection! Exiting FaultRTLIL pass doing nothing.\n");
			return;
		}

		if ((insert_cnt && !local_cnt) || timing) {
			for (auto module : design->modules()) {
				if (!module->get_bool_attribute(ID::top)) {
					log_warning("Can't create global counter or clock if the design is not flattened.\n");
					log_warning("Exiting FaultRTLIL pass doing nothing.\n");
					return;
				}
			}
		}

		std::vector<Wire *> fault_selectors;

		for (auto module : design->selected_modules()) {
			if (GetSize(module->selected_cells()) != 0)
				log_warning("Can't inject fault on cells! Please do not include cells in the selection.\n");
			for (auto wire : module->selected_wires()) {
				if (wire->get_bool_attribute("\\fauted")) {
					log_warning("Can't inject fault in signal '%s'! It is already targetted by FI.\n", log_id(wire));
					continue;
				}
				wire->set_bool_attribute("\\fauted");
				log("Injecting FAULT in signal '%s' (module \"%s\")\n", log_id(wire), log_id(module));

				// Create Mux
				Wire *new_q = module->addWire(NEW_ID, wire->width);
				Wire *fault_wire = module->addWire(stringf("%s_fault", wire->name.c_str()), wire->width);
				Wire *fault_sel = module->addWire(stringf("%s_fault_sel", wire->name.c_str()));
				fault_sel->attributes[ID::keep] = true;
				fault_selectors.push_back(fault_sel);

				// To generate Btor model, init values needs to be on the wire after the FF elements.
				// So, when adding muxes, we need to move the init value on the newly created wire
				// In addition, we need to remove old init value to allow fault injection in the init state
				if (wire->attributes.count(ID::init)) {
					new_q->attributes[ID::init] = wire->attributes.at(ID::init);
					wire->attributes.erase(ID::init);
				}

				// When the wire is an input we need to insert the fault controller after the wire
				if (wire->port_input) {
					for (auto cell : vector<Cell *>(module->cells()))
						for (auto &conn : cell->connections())
							if (cell->input(conn.first)) {
								vector<SigChunk> chunks = conn.second.chunks();
								for (auto &chunk : chunks)
									if (chunk.wire == wire)
										chunk.wire = new_q;
								cell->setPort(conn.first, chunks);
							}
					auto n = wire->name;
					module->rename(new_q, stringf("%s_copy", n.c_str()));
					// Create and connect the mux
					module->addMux(NEW_ID, wire, fault_wire, fault_sel, new_q);

				} else {
					// Connect cell output ports to the fault controller
					for (auto cell : vector<Cell *>(module->cells())) {
						for (auto &conn : cell->connections())
							if (cell->output(conn.first)) {
								vector<SigChunk> chunks = conn.second.chunks();
								for (auto &chunk : chunks)
									if (chunk.wire == wire)
										chunk.wire = new_q;
								cell->setPort(conn.first, chunks);
							}
					}

					// Handle constants driving the wire
					// Let makes the assumption that connections is Pair<SigSpec lhs, SigSpec rhs> such that lhs <- rhs
					// We just need to test lhs as we want to modify connection in order to obtain: new_q <- rhs
					std::vector<SigSig> new_conns;
					for (auto &conn : module->connections()) {
						auto lhs = conn.first.to_sigbit_vector();
						for (size_t i = 0; i < lhs.size(); i++) {
							if (lhs[i].wire == wire) {
								lhs[i].wire = new_q;
							}
						}
						new_conns.push_back(SigSig(lhs, conn.second));
					}
					module->new_connections(new_conns);

					// Create and connect the mux
					module->addMux(NEW_ID, new_q, fault_wire, fault_sel, wire);
				}

				if (permanent) {
					module->connect(fault_sel, Const(1, 1));
				}

				// Insert cnt
				else if (insert_cnt && local_cnt) {
					log("Creating Fault CNT for signal %s.%s\n", log_id(module), log_id(wire));
					Wire *wire_cnt = module->addWire(stringf("%s_fault_cnt", wire->name.c_str()), CNT_WIDTH);
					Wire *wire_b = module->addWire(NEW_ID, CNT_WIDTH);
					wire_b->attributes[ID::keep] = true;
					wire_b->attributes[ID::init] = Const(0, CNT_WIDTH);

					module->addFf(NEW_ID, wire_cnt, wire_b);
					module->addAdd(NEW_ID, wire_b, fault_sel, wire_cnt);

					// Add constraint on cnt
					if (cnt_bound >= 0) {
						log("Adding constraint %s_fault_cnt <= %d\n", wire->name.c_str(), cnt_bound);
						SigSpec le = module->Le(NEW_ID, wire_cnt, Const(cnt_bound, CNT_WIDTH));
						module->addAssume(NEW_ID, le, State::S1);
					}
				}

				// Add constraint on fault effect
				if (effect != SYMBOLIC) {
					SigSpec diff;
					switch (effect) {
					case DIFF:
						log("Constrain fault effect to DIFF\n");
						diff = module->Ne(NEW_ID, fault_wire, new_q);
						module->addAssume(NEW_ID, diff, State::S1);
						break;
					case FIXED:
						log("Constrain fault effect to FIXED\n");
						// diff = module->Eq(NEW_ID, fault_wire, Const(effect_value, fault_wire->width));
						module->connect(fault_wire, Const(effect_value, fault_wire->width));
						break;
					// case SET:
					// 	log("SET\n");
					// 	diff = module->Eq(NEW_ID, fault_wire, Const(0, fault_wire->width));
					// 	break;
					case RESET:
						log("Constrain fault effect to RESET\n");
						module->connect(fault_wire, Const(0, fault_wire->width));
						break;
					default:
						continue;
					}
				}
			}
		}

		if (timing) {
			log("Creating Global Clock for Fault Timing\n");
			RTLIL::Module *topmod = design->top_module();
			Wire *wire_clock = topmod->addWire(stringf("\\global_fault_clock"), CLK_WIDTH);
			wire_clock->attributes[ID::keep] = true;
			wire_clock->attributes[ID::init] = Const(0, CLK_WIDTH);
			topmod->addFf(NEW_ID, topmod->Add(NEW_ID, wire_clock, State::S1), wire_clock);

			SigSpec reduceor_fault_sel = State::S0;
			for (auto fault_sel : fault_selectors) {
				reduceor_fault_sel = topmod->Or(NEW_ID, reduceor_fault_sel, fault_sel);
			}
			reduceor_fault_sel = topmod->Not(NEW_ID, reduceor_fault_sel);

			SigSpec in_timing_bound = topmod->And(NEW_ID, topmod->Ge(NEW_ID, wire_clock, Const(timing_lbound, CLK_WIDTH)),
							      topmod->Le(NEW_ID, wire_clock, Const(timing_ubound, CLK_WIDTH)));

			topmod->addAssume(NEW_ID, topmod->Or(NEW_ID, in_timing_bound, reduceor_fault_sel), State::S1);
		}

		if (insert_cnt && !local_cnt) {
			RTLIL::Module *topmod = design->top_module();
			if (topmod->get_bool_attribute("\\global_fault_cnt")) {
				log_warning("Can't create new global fault counter ! There is already one in module '%s'.\n", log_id(topmod));
				return;
			}
			topmod->set_bool_attribute("\\global_fault_cnt");

			log("Creating Global Fault CNT\n");
			Wire *global_fault_cnt = topmod->addWire(stringf("\\global_fault_cnt"), CNT_WIDTH);
			Wire *wire_a = topmod->addWire(NEW_ID, CNT_WIDTH);
			wire_a->attributes[ID::keep] = true;
			wire_a->attributes[ID::init] = Const(0, CNT_WIDTH);

			// Chain to add fault_sel values with the global cnt value
			SigSpec wire_tmp = Const(0, CNT_WIDTH);
			for (auto fault_sel : fault_selectors) {
				wire_tmp = topmod->Mux(NEW_ID, wire_tmp, topmod->Add(NEW_ID, wire_tmp, State::S1), fault_sel);
				// wire_tmp = topmod->Add(NEW_ID, fault_sel, wire_tmp);
			}

			// Wire_tmp is the global fault cnt increment
			topmod->rename(wire_tmp.as_wire(), stringf("\\fault_cnt_incr"));

			// Add the previous fault cnt value with the current fault increment
			topmod->addAdd(NEW_ID, wire_a, wire_tmp, global_fault_cnt);

			// Connect the addition result to the FF cnt
			topmod->addFf(NEW_ID, global_fault_cnt, wire_a);

			// Add constraint on global cnt
			if (cnt_bound >= 0) {
				log("Adding constraint global_fault_cnt <= %d\n", cnt_bound);
				SigSpec le = topmod->Le(NEW_ID, global_fault_cnt, Const(cnt_bound, CNT_WIDTH));
				topmod->addAssume(NEW_ID, le, State::S1);
			}
		}

		log_push();
		Pass::call(design, "setundef -undriven -expose");
		log_pop();
	}
} FaultRTLILPass;

PRIVATE_NAMESPACE_END
