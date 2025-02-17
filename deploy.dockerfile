FROM python:3.13 AS build

RUN apt update && apt install -y --no-install-recommends curl ca-certificates
RUN apt install -y inkscape libcanberra-gtk-module libcanberra-gtk3-module sqlite3

RUN wget -qO- https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin/:$PATH"

COPY pyproject.toml pyproject.toml
COPY uv.lock uv.lock
COPY src/ src/
RUN echo "Empty README for building in container" > README.md

RUN uv build --wheel

FROM build

RUN find dist/ -name *.whl -print0 | xargs -0 -n1 uv tool install

COPY scripts/ssh_add.sh /root/.local/bin/ssh_add.sh
COPY scripts/entrypoint.sh /root/.local/bin/entrypoint.sh


