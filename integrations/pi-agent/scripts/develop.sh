#!/bin/bash
set -euo pipefail

# ---------------------------------------------------------------------------
# develop.sh — local-dev toggle for @open-cursor/pi-agent
#
# Usage:
#   ./scripts/develop.sh link        # symlink local copy + remove npm version
#   ./scripts/develop.sh unlink      # remove local symlink + reinstall npm version
#   ./scripts/develop.sh status      # show current installation state
#
# After link/unlink, run `/reload` inside the Pi CLI to pick up the
# changes.
# ---------------------------------------------------------------------------

readonly PROJECT_NAME="@open-cursor/pi-agent"
readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly PACKAGE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly EXT_DIR="${HOME}/.pi/agent/extensions"
readonly SYMLINK="${EXT_DIR}/open-cursor-pi-agent"
readonly NPM_NAME="npm:${PROJECT_NAME}"

# --- helpers ----------------------------------------------------------------

die() {
	echo "[dev] ERROR: $*" >&2
	exit 1
}

info() { echo "[dev] $*"; }
pi_cmd() { echo "    Pi >   $*"; }

assert_package() {
	[[ -d "${PACKAGE_DIR}" ]] || die "package dir not found: ${PACKAGE_DIR}"
	[[ -f "${PACKAGE_DIR}/package.json" ]] || die "no package.json in ${PACKAGE_DIR}"
	[[ -d "${PACKAGE_DIR}/src" ]] || die "no src/ in ${PACKAGE_DIR}"
}

ensure_ext_dir() {
	mkdir -p "${EXT_DIR}" || die "cannot create ${EXT_DIR}"
}

require_pi_cli() {
	command -v pi >/dev/null 2>&1 || die "pi CLI not found on PATH"
}

# Returns 0 if the npm extension appears installed in Pi settings.
npm_extension_installed() {
	pi list 2>/dev/null | grep -q "${NPM_NAME}"
}

# --- subcommands ------------------------------------------------------------

cmd_link() {
	require_pi_cli
	assert_package
	ensure_ext_dir

	# Step 1: remove any existing file/symlink at the target path, then
	#         create a fresh symlink.
	if [[ -L "${SYMLINK}" ]] || [[ -e "${SYMLINK}" ]]; then
		local old_target=""
		[[ -L "${SYMLINK}" ]] && old_target=$(readlink "${SYMLINK}")
		rm -rf "${SYMLINK}" || die "failed to remove existing path at ${SYMLINK}"
		if [[ -n "${old_target}" ]]; then
			info "removed old symlink -> ${old_target}"
		else
			info "removed existing path at ${SYMLINK}"
		fi
	fi
	ln -s "${PACKAGE_DIR}" "${SYMLINK}" || die "failed to create symlink"
	info "linked ${PACKAGE_DIR} -> ${SYMLINK}"

	# Step 2: uninstall the npm version to avoid tool conflicts.
	if npm_extension_installed; then
		info "uninstalling npm version (${NPM_NAME})..."
		pi uninstall "${NPM_NAME}" || die "pi uninstall failed"
	else
		info "npm version not installed; nothing to uninstall"
	fi

	# Step 3: tell the user to /reload inside Pi.
	cat <<-EOM

	[dev] DONE. Now run inside the Pi CLI:
	$(pi_cmd "/reload")

	[dev] Verify by checking the provider list:
	$(pi_cmd "/model")                # should show cursor-agent models

	[dev] When done developing, switch back to the published npm version:
	$(echo "    Terminal\$  ${SCRIPT_DIR}/develop.sh unlink")
	EOM
}

cmd_unlink() {
	require_pi_cli

	# Step 1: remove the dev symlink.
	if [[ -L "${SYMLINK}" ]]; then
		local target
		target=$(readlink "${SYMLINK}")
		rm "${SYMLINK}" || die "failed to remove symlink"
		info "removed symlink -> ${target}"
	else
		info "no dev symlink at ${SYMLINK}"
	fi

	# Step 2: reinstall the published npm package as a Pi extension.
	info "installing npm version (${NPM_NAME})..."
	pi install "${NPM_NAME}" || die "pi install failed"

	# Step 3: tell the user to /reload inside Pi.
	cat <<-EOM

	[dev] DONE. Now run inside the Pi CLI:
	$(pi_cmd "/reload")

	[dev] Verify with:
	$(pi_cmd "/model")
	EOM
}

cmd_status() {
	local symlink_state="none"
	if [[ -L "${SYMLINK}" ]]; then
		symlink_state="symlinked"
	elif [[ -e "${SYMLINK}" ]]; then
		symlink_state="non-symlink"
	fi

	local npm_state="not installed"
	if command -v pi >/dev/null 2>&1 && npm_extension_installed; then
		npm_state="installed"
	fi

	echo "package:   ${PROJECT_NAME}"
	echo "local dir: ${PACKAGE_DIR}"
	echo "symlink:   ${symlink_state}  (${SYMLINK})"
	if [[ "${symlink_state}" == "symlinked" ]]; then
		echo "  target:    $(readlink "${SYMLINK}")"
	fi
	echo "npm:       ${npm_state}  (${NPM_NAME})"
	echo

	if [[ "${symlink_state}" == "symlinked" && "${npm_state}" == "installed" ]]; then
		echo "WARNING: both dev symlink and npm version are active."
		echo "Tool conflicts may occur. Run: ${SCRIPT_DIR}/develop.sh link"
	elif [[ "${symlink_state}" == "symlinked" ]]; then
		echo "state: DEV (local copy active)"
	elif [[ "${npm_state}" == "installed" ]]; then
		echo "state: NPM (published version active)"
	else
		echo "state: NONE (extension not installed)"
	fi
}

cmd_help() {
	cat <<-EOF
	Usage: ${0##*/} <command>

	Commands:
	  link      Symlink local project into Pi extensions AND remove the
	            published npm version. Tells you to run /reload.
	  unlink    Remove dev symlink AND reinstall the published npm version.
	            Tells you to run /reload.
	  status    Show whether dev symlink and/or npm version are active.
	  help      Show this message.

	After link/unlink, run /reload inside the Pi CLI to pick up changes.

	Typical flow:
	  1. Terminal: ${0##*/} link
	  2. Pi CLI:   /reload
	  3. Pi CLI:   try cursor-agent
	  4. Terminal: ${0##*/} unlink
	  5. Pi CLI:   /reload
	EOF
}

# --- main -------------------------------------------------------------------

COMMAND="${1:-help}"

case "${COMMAND}" in
link) cmd_link ;;
unlink) cmd_unlink ;;
status) cmd_status ;;
help | --help | -h) cmd_help ;;
*) die "unknown command: ${COMMAND}. Try 'help'." ;;
esac
