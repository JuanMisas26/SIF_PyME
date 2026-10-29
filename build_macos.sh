#!/usr/bin/env bash
# Forwarder de conveniencia hacia scripts/build_macos.sh
chmod +x "$(dirname "$0")/scripts/build_macos.sh" 2>/dev/null || true
exec "$(dirname "$0")/scripts/build_macos.sh" "$@"
