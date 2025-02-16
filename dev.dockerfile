FROM python:3.13

RUN apt update && apt install -y --no-install-recommends curl ca-certificates
RUN apt install -y inkscape libcanberra-gtk-module libcanberra-gtk3-module sqlite3

RUN wget -qO- https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin/:$PATH"
RUN pip install pre-commit