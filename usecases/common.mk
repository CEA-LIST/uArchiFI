YOSYS_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))../build/yosys
YOSYS_CMD = $(YOSYS_DIR)/yosys

SCRIPT := ${CURRENT_DIR}/script
SRC    := ${CURRENT_DIR}/src
OUT    := ${CURRENT_DIR}/out

PIPE_TIME := | ts '[%Y-%m-%d %H:%M:%.S]'
YOSYS_SMT := yices
YOSYS_OPTIONS =
PONO_SMT  := btor


mkdir_out:
	mkdir -p "out"

btormc: check_btormc_deps
	time btormc --stop-first 1 -v 1 -kmax $(BMC_DEPTH) $(OUT)/$(BASE_NAME).btor2 $(PIPE_TIME)

pono: check_pono_deps
	time pono --smt-solver $(PONO_SMT) --witness -v 2 -e bmc -k $(BMC_DEPTH) $(OUT)/$(BASE_NAME).btor2 $(PIPE_TIME)

yosysmc: check_yices2_deps
	time yosys-smtbmc -t $(BMC_DEPTH) -s $(YOSYS_SMT) --presat $(YOSYS_OPTIONS) $(OUT)/$(BASE_NAME).smt2 $(PIPE_TIME)

check_pono_deps:
	@if ! command -v pono >/dev/null 2>&1; then echo "Please install pono (https://github.com/upscale-project/pono)"; exit 1; fi

check_btormc_deps:
	@if ! command -v btormc >/dev/null 2>&1; then echo "Please install btormc (https://github.com/Boolector/boolector)"; exit 1; fi

check_yices2_deps:
	@if ! command -v yices-smt2 >/dev/null 2>&1; then echo "Please install yices2 (https://github.com/SRI-CSL/yices2)"; exit 1; fi

check_yosys_build:
ifeq (,$(wildcard $(YOSYS_CMD)))
	$(error "yosys command does not exist! Please run 'make build' in the root directory first")
endif

clean:
	rm -rf out
