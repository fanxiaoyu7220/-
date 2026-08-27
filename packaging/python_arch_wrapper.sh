#!/bin/zsh
set -e

if [ -z "${ACAN_REAL_PYTHON:-}" ] || [ -z "${ACAN_PYTHON_ARCH:-}" ]; then
  echo "ACAN Python wrapper is missing ACAN_REAL_PYTHON or ACAN_PYTHON_ARCH." >&2
  exit 64
fi

exec /usr/bin/arch "-$ACAN_PYTHON_ARCH" /usr/bin/env \
  "DYLD_FRAMEWORK_PATH=${ACAN_RUNTIME_FRAMEWORK_PATH:-}" \
  "DYLD_LIBRARY_PATH=${ACAN_RUNTIME_LIBRARY_PATH:-}" \
  "TCL_LIBRARY=${ACAN_RUNTIME_TCL_LIBRARY:-}" \
  "TK_LIBRARY=${ACAN_RUNTIME_TK_LIBRARY:-}" \
  "SSL_CERT_FILE=${ACAN_RUNTIME_SSL_CERT_FILE:-/etc/ssl/cert.pem}" \
  "$ACAN_REAL_PYTHON" "$@"
