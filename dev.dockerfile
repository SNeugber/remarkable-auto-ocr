FROM python:3.13

RUN apt update && apt install -y --no-install-recommends curl ca-certificates
RUN apt install -y inkscape libcanberra-gtk-module libcanberra-gtk3-module sqlite3

ADD https://astral.sh/uv/install.sh /uv-installer.sh

RUN sh /uv-installer.sh && rm /uv-installer.sh

RUN pip install pre-commit

ENV PATH="/root/.local/bin/:$PATH"