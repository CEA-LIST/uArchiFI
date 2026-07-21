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

BUILD_DIR = $(shell realpath build)
YOSYS_TAG = yosys-0.61
YOSYS_CMD = $(shell which yosys)
FAULT_PASS = fault_rtlil


.PHONY: install help check_yosys

help:
	@echo "run 'make install' to build the fault_rtlil pass"
	@echo "default install location : /home/oss-cad-suite/share/yosys/plugins"

fault_rtlil: check_yosys $(BUILD_DIR)
	yosys-config --build $(BUILD_DIR)/$(FAULT_PASS).so ./src/passes/fault/$(FAULT_PASS).cc 

install: fault_rtlil
	cp $(BUILD_DIR)/$(FAULT_PASS).so /home/oss-cad-suite/share/yosys/plugins

$(BUILD_DIR):
	mkdir -p $@

check_yosys:
ifeq (,$(wildcard $(YOSYS_CMD)))
	@echo "yosys command not found!"
endif

clean:
	rm -rf $(BUILD_DIR)
