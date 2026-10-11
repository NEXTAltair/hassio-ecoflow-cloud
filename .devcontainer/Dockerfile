# Same Debian + uv approach as Home Assistant's release development image.
FROM mcr.microsoft.com/devcontainers/base:debian@sha256:6ee2b4097c75d33e9a94d941577a3286e5d629434fba384688b06daeeaaeac99

COPY --from=ghcr.io/astral-sh/uv:0.13.0@sha256:cdc6093146eb3ff6a40107b38f008b789e050e77ad87865e381d9917da55a168 /uv /uvx /usr/local/bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

ARG PYTHON_VERSION=3.14.6
ENV VIRTUAL_ENV=/home/vscode/.local/ha-venv \
    UV_PROJECT_ENVIRONMENT=/home/vscode/.local/ha-venv \
    UV_PYTHON_INSTALL_DIR=/home/vscode/.local/share/uv/python \
    PYTHONDONTWRITEBYTECODE=1
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

COPY --chown=vscode:vscode requirements.lock /tmp/requirements.lock
USER vscode
RUN --mount=type=cache,target=/home/vscode/.cache/uv,uid=1000,gid=1000 \
    uv python install "${PYTHON_VERSION}" \
    && uv venv --python "${PYTHON_VERSION}" "${VIRTUAL_ENV}" \
    && uv pip sync --python "${VIRTUAL_ENV}/bin/python" --link-mode=copy --require-hashes /tmp/requirements.lock

WORKDIR /workspace
CMD ["sleep", "infinity"]
