CURRENT_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
include ${CURRENT_DIR}/../common.mk

BMC_DEPTH := <depth>
BASE_NAME := <design>
YOSYS_OPTIONS := --dump-vcd $(OUT)/counter_example.vcd

prep_baseline: check_yosys_build mkdir_out
	$(YOSYS_CMD) ${SCRIPT}/prep_pass.ys
	$(YOSYS_CMD) ${SCRIPT}/simu.ys
	$(YOSYS_CMD) ${SCRIPT}/apply_faults.ys
