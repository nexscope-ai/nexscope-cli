#!/bin/sh
# Nexscope CLI installer for macOS and Linux.
#
#   curl -fsSL https://raw.githubusercontent.com/nexscope-ai/nexscope-cli/main/install.sh | sh
#
# Downloads the standalone nexscope binary from GitHub Releases, verifies its SHA-256
# checksum and installs it. No Python needed. On Windows, use install.ps1.

set -eu

REPO="nexscope-ai/nexscope-cli"
BINARY="nexscope"
DOWNLOAD_URL="${NEXSCOPE_DOWNLOAD_URL:-https://github.com/${REPO}/releases/download}"

VERSION="${NEXSCOPE_VERSION:-}"
PREFIX=""
VERIFY="yes"
MODIFY_PATH="yes"

say() { printf '%s\n' "$*"; }
err() { printf 'error: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || err "'$1' is required but was not found on PATH"; }

# Written out here because `curl | sh` gives the script no file to read its header from.
usage() {
  cat <<'USAGE'
Nexscope CLI installer for macOS and Linux.

  curl -fsSL https://raw.githubusercontent.com/nexscope-ai/nexscope-cli/main/install.sh | sh

Options (pass them after `sh -s --`):
  --version <x.y.z>   install this version instead of the latest release
  --prefix <dir>      install to <dir>/bin (default: /usr/local if writable, else ~/.local)
  --no-modify-path    do not add the install directory to your shell profile
  --no-verify         skip the SHA-256 checksum check (not recommended)
  -h, --help          show this message

  curl -fsSL .../install.sh | sh -s -- --version 0.1.2
USAGE
  exit 0
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --version) [ "$#" -ge 2 ] || err "--version needs a value"; VERSION="$2"; shift 2 ;;
    --version=*) VERSION="${1#*=}"; shift ;;
    --prefix) [ "$#" -ge 2 ] || err "--prefix needs a value"; PREFIX="$2"; shift 2 ;;
    --prefix=*) PREFIX="${1#*=}"; shift ;;
    --no-modify-path) MODIFY_PATH="no"; shift ;;
    --no-verify) VERIFY="no"; shift ;;
    -h|--help) usage ;;
    *) err "unknown option '$1' (try --help)" ;;
  esac
done

need curl
need tar

# Only plain HTTPS for real downloads; a local mirror set through NEXSCOPE_DOWNLOAD_URL may use http.
case "$DOWNLOAD_URL" in
  https://*) fetch() { curl -fsSL --proto '=https' --tlsv1.2 "$@"; } ;;
  *) fetch() { curl -fsSL "$@"; } ;;
esac

# --- Platform ---------------------------------------------------------------

os="$(uname -s | tr '[:upper:]' '[:lower:]')"
case "$os" in
  darwin|linux) ;;
  mingw*|msys*|cygwin*) err "on Windows, run install.ps1 in PowerShell instead (see https://github.com/${REPO}#install)" ;;
  *) err "unsupported operating system '$os'" ;;
esac

arch="$(uname -m)"
case "$arch" in
  x86_64|amd64) arch="amd64" ;;
  arm64|aarch64) arch="arm64" ;;
  *) err "unsupported architecture '$arch'; builds exist for amd64 and arm64" ;;
esac

# Rosetta reports x86_64 on Apple Silicon; prefer the native build.
if [ "$os" = "darwin" ] && [ "$arch" = "amd64" ] && [ "$(sysctl -n sysctl.proc_translated 2>/dev/null || echo 0)" = "1" ]; then
  arch="arm64"
fi

if [ -z "$VERSION" ]; then
  VERSION="$(fetch "https://api.github.com/repos/${REPO}/releases/latest" |
    sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -n 1)"
  [ -n "$VERSION" ] || err "could not find the latest release (GitHub may be rate-limiting); retry or pass --version"
fi
VERSION="${VERSION#v}"

ARCHIVE="${BINARY}_${VERSION}_${os}_${arch}.tar.gz"
BASE_URL="${DOWNLOAD_URL}/v${VERSION}"

# --- Destination ------------------------------------------------------------

# Closest existing directory, so a missing ~/.local is not mistaken for an unwritable one.
existing_ancestor() {
  dir="$1"
  while [ ! -e "$dir" ]; do
    parent="$(dirname "$dir")"
    [ "$parent" = "$dir" ] && break
    dir="$parent"
  done
  printf '%s\n' "$dir"
}

# Never prompt for sudo unasked: use /usr/local/bin only when it is already writable.
if [ -z "$PREFIX" ]; then
  if [ -w "$(existing_ancestor /usr/local/bin)" ]; then
    PREFIX="/usr/local"
  else
    PREFIX="${HOME}/.local"
  fi
fi
BIN_DIR="${PREFIX}/bin"

# --- Download and verify ----------------------------------------------------

tmp="$(mktemp -d)"
# shellcheck disable=SC2064 # expand $tmp now
trap "rm -rf '$tmp'" EXIT INT TERM

say "Downloading ${BINARY} ${VERSION} (${os}/${arch})..."
fetch -o "${tmp}/${ARCHIVE}" "${BASE_URL}/${ARCHIVE}" ||
  err "could not download ${BASE_URL}/${ARCHIVE}; is ${VERSION} a released version with binaries?"

if [ "$VERIFY" = "yes" ]; then
  if command -v sha256sum >/dev/null 2>&1; then
    actual="$(sha256sum "${tmp}/${ARCHIVE}" | cut -d' ' -f1)"
  elif command -v shasum >/dev/null 2>&1; then
    actual="$(shasum -a 256 "${tmp}/${ARCHIVE}" | cut -d' ' -f1)"
  else
    err "no sha256sum or shasum found to verify the download; install one or pass --no-verify"
  fi
  fetch -o "${tmp}/checksums.txt" "${BASE_URL}/checksums.txt" ||
    err "could not download checksums.txt for ${VERSION}"
  expected="$(awk -v want="$ARCHIVE" '$2 == want || $2 == "*" want { print $1 }' "${tmp}/checksums.txt")"
  [ -n "$expected" ] || err "${ARCHIVE} is not listed in checksums.txt"
  [ "$actual" = "$expected" ] ||
    err "checksum mismatch for ${ARCHIVE}: got ${actual}, expected ${expected}. Do not use this download."
  say "Checksum verified."
fi

tar -xzf "${tmp}/${ARCHIVE}" -C "$tmp"
[ -f "${tmp}/${BINARY}" ] || err "the archive does not contain '${BINARY}'"

# --- Install ----------------------------------------------------------------

as_owner() {
  if [ -w "$(existing_ancestor "$BIN_DIR")" ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    err "${BIN_DIR} is not writable and sudo is unavailable; re-run with --prefix \"\$HOME/.local\""
  fi
}

[ -d "$BIN_DIR" ] || as_owner mkdir -p "$BIN_DIR"
as_owner install -m 0755 "${tmp}/${BINARY}" "${BIN_DIR}/${BINARY}"

# Gatekeeper can block a downloaded binary on first run; it is ad-hoc signed but not notarized.
if [ "$os" = "darwin" ]; then
  xattr -d com.apple.quarantine "${BIN_DIR}/${BINARY}" 2>/dev/null || true
fi

say ""
say "Installed ${BINARY} $("${BIN_DIR}/${BINARY}" --version) to ${BIN_DIR}/${BINARY}"

# --- PATH -------------------------------------------------------------------

on_path="no"
case ":${PATH}:" in *":${BIN_DIR}:"*) on_path="yes" ;; esac

if [ "$on_path" = "no" ] && [ "$MODIFY_PATH" = "yes" ]; then
  case "$(basename "${SHELL:-sh}")" in
    zsh) profile="${ZDOTDIR:-$HOME}/.zshrc" ;;
    bash) if [ "$os" = "darwin" ]; then profile="${HOME}/.bash_profile"; else profile="${HOME}/.bashrc"; fi ;;
    fish) profile="" ;;
    *) profile="${HOME}/.profile" ;;
  esac
  line="export PATH=\"${BIN_DIR}:\$PATH\""
  if [ -n "$profile" ]; then
    if ! grep -qsF "$line" "$profile"; then
      printf '\n# Added by the Nexscope CLI installer\n%s\n' "$line" >> "$profile"
      say "Added ${BIN_DIR} to your PATH in ${profile}."
    fi
    say ""
    say "Open a new terminal, or run this once in the current one:"
    say ""
    say "  ${line}"
  else
    say ""
    say "Add ${BIN_DIR} to your PATH:  fish_add_path ${BIN_DIR}"
  fi
elif [ "$on_path" = "no" ]; then
  say ""
  say "${BIN_DIR} is not on your PATH. Add it with:"
  say ""
  say "  export PATH=\"${BIN_DIR}:\$PATH\""
fi

# A pip-installed nexscope earlier on PATH would shadow this binary.
found="$(command -v "$BINARY" 2>/dev/null || true)"
if [ "$on_path" = "yes" ] && [ -n "$found" ] && [ "$found" != "${BIN_DIR}/${BINARY}" ]; then
  say ""
  say "note: '${BINARY}' currently resolves to ${found}, which comes before ${BIN_DIR} on your PATH."
fi

say ""
say "Get started:"
say "  ${BINARY} doctor --offline"
say "  ${BINARY} tools list --search amazon"
