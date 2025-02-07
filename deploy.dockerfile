FROM python:3.13 as build

RUN apt update && apt install -y --no-install-recommends curl ca-certificates
RUN apt install -y inkscape libcanberra-gtk-module libcanberra-gtk3-module sqlite3

ADD https://astral.sh/uv/install.sh /uv-installer.sh

RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin/:$PATH"

COPY pyproject.toml pyproject.toml
COPY uv.lock uv.lock
COPY README.md README.md
COPY src/ src/

RUN uv build --wheel

FROM build

RUN find dist/ -name *.whl -exec uv tool install {} ';'


