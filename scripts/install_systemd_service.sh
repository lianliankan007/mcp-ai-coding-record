#!/usr/bin/env bash
set -euo pipefail

if [[ "${OSTYPE:-}" != linux* ]]; then
  echo "This installer only supports Linux with systemd." >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not found. This host does not appear to use systemd." >&2
  exit 1
fi

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root or via sudo." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_NAME="${SERVICE_NAME:-memory-mcp-server}"
SERVICE_USER="${SERVICE_USER:-${SUDO_USER:-root}}"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env}"
START_SCRIPT="${START_SCRIPT:-${ROOT_DIR}/scripts/start.sh}"
TEMPLATE_PATH="${SCRIPT_DIR}/memory-mcp-server.service.template"
TARGET_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Environment file not found: ${ENV_FILE}" >&2
  echo "Copy .env.example to .env and fill in the required values first." >&2
  exit 1
fi

if [[ ! -x "${START_SCRIPT}" ]]; then
  echo "Start script is not executable: ${START_SCRIPT}" >&2
  echo "Run: chmod +x ${START_SCRIPT}" >&2
  exit 1
fi

if [[ ! -f "${TEMPLATE_PATH}" ]]; then
  echo "Service template not found: ${TEMPLATE_PATH}" >&2
  exit 1
fi

tmp_file="$(mktemp)"
trap 'rm -f "${tmp_file}"' EXIT

sed \
  -e "s|__SERVICE_USER__|${SERVICE_USER}|g" \
  -e "s|__ROOT_DIR__|${ROOT_DIR}|g" \
  -e "s|__ENV_FILE__|${ENV_FILE}|g" \
  -e "s|__START_SCRIPT__|${START_SCRIPT}|g" \
  "${TEMPLATE_PATH}" > "${tmp_file}"

install -m 0644 "${tmp_file}" "${TARGET_PATH}"
systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}"

echo "Installed and started ${SERVICE_NAME}."
echo "Check status with: systemctl status ${SERVICE_NAME}"
echo "View logs with: journalctl -u ${SERVICE_NAME} -f"
