#!/usr/bin/env bash
# Install the pinned official Linux x64 release into a new, caller-owned directory.
set -euo pipefail

if [[ $# -ne 1 || -z "$1" ]]; then
  echo "Usage: bash $0 NEW_DESTINATION" >&2
  exit 2
fi
if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
  echo 'This helper supports Linux x64 only.' >&2
  exit 2
fi
if [[ -e "$1" || -L "$1" ]]; then
  echo 'Destination already exists; refusing to replace it.' >&2
  exit 2
fi

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
version=$(cat "$root/bend-version")
digest=$(cat "$root/bend-linux-x64.sha256")
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
[[ "$digest" =~ ^[0-9a-f]{64}$ ]]
archive="bend-$version-linux-x64.tar.gz"
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
curl --proto '=https' --tlsv1.2 --fail --location --max-time 120 --silent --show-error \
  "https://github.com/bendlang/bend/releases/download/v$version/$archive" \
  --output "$tmp/$archive"
printf '%s  %s\n' "$digest" "$tmp/$archive" | sha256sum -c -
mkdir -- "$1"
tar --warning=no-unknown-keyword -xzf "$tmp/$archive" -C "$1"
BEND_NO_TELEMETRY=1 "$1/bend/bin/bend" version
