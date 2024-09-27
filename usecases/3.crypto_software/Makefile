CURRENT_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
include ${CURRENT_DIR}/../common.mk

BMC_DEPTH := 38
BASE_NAME := simple_ibex_aes

prep_baseline: check_yosys_build mkdir_out
	$(YOSYS_CMD) ${SCRIPT}/build.ys

prep_sandboxing: check_yosys_build mkdir_out
	$(YOSYS_CMD) ${SCRIPT}/build_sandboxing.ys
