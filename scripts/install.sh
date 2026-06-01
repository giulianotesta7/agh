#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

if [[ ! -f "${repo_root}/pyproject.toml" || ! -d "${repo_root}/agh" ]]; then
	echo "Error: could not find the AGH repo root." >&2
	echo "Run this script from an AGH checkout." >&2
	exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
	echo "Error: uv is required to install the agh CLI." >&2
	echo "Install uv first: https://docs.astral.sh/uv/getting-started/installation/" >&2
	exit 1
fi

echo "Installing agh CLI from ${repo_root}..."
uv tool install --force "${repo_root}"

if command -v agh >/dev/null 2>&1; then
	if agh --help >/dev/null 2>&1; then
		echo "Installed agh: $(command -v agh)"
		echo "Run: agh --help"
		exit 0
	fi
	echo "Error: agh is on PATH but 'agh --help' failed." >&2
	exit 1
fi

echo "agh was installed, but this shell cannot find it on PATH yet."
echo
echo "Run:"
echo "  uv tool update-shell"
echo
echo "Then restart your shell and verify:"
echo "  agh --help"

if tool_dir="$(uv tool dir 2>/dev/null)"; then
	echo
	echo "uv tool directory: ${tool_dir}"
fi
