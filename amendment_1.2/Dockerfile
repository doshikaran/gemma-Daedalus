# Linux x86_64 restoration environment for protocol 1.1 (amendment 1.2).
# Runs as linux/amd64 under Rosetta inside a Lima vz VM on Apple Silicon.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl xz-utils git gcc g++ make libgomp1 libcurl4 rsync procps \
    && rm -rf /var/lib/apt/lists/*
# uv 0.13.4 (protocol.environment.uv)
RUN curl -fsSL https://github.com/astral-sh/uv/releases/download/0.13.4/uv-x86_64-unknown-linux-gnu.tar.gz \
      | tar -xz -C /usr/local/bin --strip-components=1
# Python 3.12.14 (protocol.environment.python)
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python
RUN uv python install 3.12.14 && ln -s "$(uv python find 3.12.14)" /usr/local/bin/python3.12 \
    && ln -sf /usr/local/bin/python3.12 /usr/local/bin/python3 && ln -sf /usr/local/bin/python3.12 /usr/local/bin/python
# Node v24.22.1 / npm 11.9.0 (protocol.environment.node/npm)
RUN curl -fsSL https://nodejs.org/dist/v24.22.1/node-v24.22.1-linux-x64.tar.xz | tar -xJ -C /opt \
    && ln -s /opt/node-v24.22.1-linux-x64 /opt/node
ENV PATH=/opt/node/bin:$PATH
RUN [ "$(npm --version)" = "11.9.0" ] || npm install -g npm@11.9.0
RUN git config --global --add safe.directory '*'
WORKDIR /workspace/scratch/93af20bbcd93/packaging_study
