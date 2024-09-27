BUILD_DIR = build
YOSYS_GIT = https://github.com/YosysHQ/yosys
YOSYS_TAG = yosys-0.25
YOSYS_DIR = $(BUILD_DIR)/yosys
YOSYS_CMD = $(YOSYS_DIR)/yosys
COMPILER  = gcc #or clang


.PHONY: build clean_yosys help check_build

help:
	@echo "run 'make build' to build yosys with the fault2mux pass"
	@echo "Further help for building yosys: https://github.com/YosysHQ/yosys#building-from-source"

build:
	@mkdir build
	@cd $(BUILD_DIR) && git clone $(YOSYS_GIT) 
	@cd $(YOSYS_DIR) && git checkout -b fault2mux $(YOSYS_TAG)
	@cp -r src/fault $(YOSYS_DIR)/passes
	@cd $(YOSYS_DIR) && make config-$(COMPILER) && make -j2

check_build:
ifeq (,$(wildcard $(YOSYS_CMD)))
	@echo "yosys command does not exist! Please run 'make build' first"
endif

clean_yosys:
	rm -rf $(BUILD_DIR)
