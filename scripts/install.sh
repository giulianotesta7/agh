#!/bin/sh
set -eu

if ! command -v uv >/dev/null 2>&1; then
	echo "Error: uv is required to install the agh CLI." >&2
	echo "Install uv first: https://docs.astral.sh/uv/getting-started/installation/" >&2
	exit 1
fi

install_package=${AGH_INSTALL_PACKAGE:-agh}

echo "Installing agh CLI package: ${install_package}"
uv tool install --force "${install_package}"

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

if tool_dir=$(uv tool dir 2>/dev/null); then
	echo
	echo "uv tool directory: ${tool_dir}"
fi
