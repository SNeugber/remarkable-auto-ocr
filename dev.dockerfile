FROM python:3.13

RUN apt update && apt install -y --no-install-recommends curl ca-certificates
RUN apt install inkscape

ADD https://astral.sh/uv/install.sh /uv-installer.sh

RUN sh /uv-installer.sh && rm /uv-installer.sh

RUN pip install pre-commit

ENV PATH="/root/.local/bin/:$PATH"