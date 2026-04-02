CURRENT_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
include ${CURRENT_DIR}/../common.mk

BMC_DEPTH := 50
BASE_NAME := secure_ibex_verifypin

prep_baseline: check_yosys_build mkdir_out
	$(YOSYS_CMD) ${SCRIPT}/parse.ys
	@sed -i 's/00000111000001100000010100000000000000110000001000000001/xxxxxxxxxxxxxxxxxxxxxxxx00000000xxxxxxxxxxxxxxxxxxxxxxxx/g' $(OUT)/$(BASE_NAME).il
	$(YOSYS_CMD) ${SCRIPT}/build.ys

prep_sandboxing: check_yosys_build mkdir_out
	$(YOSYS_CMD) ${SCRIPT}/parse_sandboxing.ys
	@sed -i 's/00000111000001100000010100000000000000110000001000000001/xxxxxxxxxxxxxxxxxxxxxxxx00000000xxxxxxxxxxxxxxxxxxxxxxxx/g' $(OUT)/$(BASE_NAME).il
	$(YOSYS_CMD) ${SCRIPT}/build_sandboxing.ys
