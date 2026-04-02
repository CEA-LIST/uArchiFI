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

# This Dockerfile targets the installation of uArchiFI with Yosys OSS CAD suite

# debian bookworm-slim
FROM debian@sha256:f528891ab1aa484bf7233dbcc84f3c806c3e427571d75510a9d74bb5ec535b33

ARG NPROC=4

# Metadata
LABEL maintainer="Damien Couroussé <damien.courousse@cea.fr>"
LABEL co-maintainer="Giorgio Fardo <giorgio.fardo@cea.fr>"

# Generic dependencies
RUN apt-get update \
 && apt-get install -y \
	autoconf \
	moreutils \
	time \
	clang \
	gawk \
	git \
	graphviz \
	libreadline-dev \
	python3 \
	python3-pip \
	python3-venv \
	tcl-dev \
	unzip \
	wget \
 && rm -rf /var/lib/apt/lists

# OSS cad suite 2026 (matching roghfly the 0.61) 
RUN wget --no-verbose \
	"https://github.com/YosysHQ/oss-cad-suite-build/releases/download/2026-01-15/oss-cad-suite-linux-x64-20260115.tgz" && \
    tar -xzf oss-cad-suite-linux-x64-20260115.tgz --directory /home && \
    rm -r oss-cad-suite-linux-x64-20260115.tgz  
ENV PATH="${PATH}:/home/oss-cad-suite/bin"

# sv2v 0.0.13
RUN wget --no-verbose \
	"https://github.com/zachjs/sv2v/releases/download/v0.0.13/sv2v-Linux.zip" && \	
	unzip sv2v-Linux.zip -d /home && \
	rm sv2v-Linux.zip
ENV PATH="${PATH}:/home/sv2v-Linux/"

# Yosys, with the fault_rtlil pass
COPY src/ /src/src/
COPY Makefile  pyproject.toml requirements.txt /src

WORKDIR /src
RUN make --jobs=${NPROC} install
RUN python3 -m venv /opt/iterator_venv
ENV PATH="/opt/iterator_venv/bin:$PATH"
RUN pip install --upgrade pip && \
	pip install .

# copy misc. files.
COPY LICENSE.txt /src/src
COPY tests /src/tests

# end of script.   Move a the source's root
WORKDIR /src
