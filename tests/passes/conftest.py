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

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--yosys-variant",
        action="store",
        required=True,
        help="Select yosys variant (e.g. 0.25 or 0.61)",
    )


@pytest.fixture(scope="session")
def yosys_variant(request):
    return request.config.getoption("--yosys-variant")
