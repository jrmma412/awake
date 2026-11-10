#!/usr/bin/env bash
# Install / uninstall awake on Linux.
#   ./linux/install.sh              install the `awake` command
#   ./linux/install.sh --uninstall  remove it
#   options: -y / --yes  don't ask, use the default location
#            --dir DIR   install into DIR instead of ~/.local/bin
#   piped:   curl ... | bash -s -- -y      (options go after "bash -s --")
# Also works piped from the web (public repo):
#   curl -fsSL https://raw.githubusercontent.com/jrmma412/awake/main/linux/install.sh | bash
# (to uninstall that way:  ... | bash -s -- --uninstall [-y])
HERE=""
[[ -n ${BASH_SOURCE[0]:-} && -f ${BASH_SOURCE[0]} ]] && HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
main() {
  local MARK="# added by awake" TAG="awake - keep your Linux PC awake"
  local REF=v1.8.0   # release the downloaded copy is pinned to
  local RAW=https://raw.githubusercontent.com/jrmma412/awake/$REF/linux/awake
  local yes=0 custom=""
  while [[ $# -gt 0 ]]; do
    case $1 in
      -y|--yes) yes=1; shift;;
      --dir) custom=${2:-}; [[ -n $custom ]] || { echo "--dir needs a folder"; return 1; }; shift 2;;
      --uninstall) break;;
      *) echo "usage: install.sh [-y] [--dir DIR] | --uninstall"; return 1;;
    esac
  done
  # Ask a yes/no question (default yes). Skips asking with -y or when there is no terminal.
  ask() {
    (( yes )) && return 0
    { : </dev/tty; } 2>/dev/null || return 0
    local a; read -r -p "$1 [Y/n] " a </dev/tty
    [[ -z $a || $a == [Yy]* ]]
  }

  if [[ ${1:-} == --uninstall ]]; then
    # The installed awake's own uninstaller does everything (agent mode, PATH line, state folder).
    shift
    local b; b=$(command -v awake 2>/dev/null)
    if [[ -n $b ]] && grep -q "$TAG" "$b" 2>/dev/null; then
      if (( yes )); then "$b" uninstall -y "$@"; else "$b" uninstall "$@"; fi
      return
    fi
    echo "awake (Linux) was not found on your PATH; nothing to uninstall."; return 1
  fi

  # Use the awake file next to this script only when run as a file (./install.sh).
  # When piped (curl | bash) there is no script file, so always download.
  local src="" tmp=""
  [[ -n $HERE && -f $HERE/awake ]] && src=$HERE/awake
  if [[ -z $src ]]; then
    tmp=$(mktemp) && curl -fsSL "$RAW" -o "$tmp" || { echo "download failed"; rm -f "$tmp"; return 1; }
    src=$tmp
  fi
  grep -q "$TAG" "$src" || { echo "unexpected file, aborting"; [[ -n $tmp ]] && rm -f "$tmp"; return 1; }

  local dest=$HOME/.local/bin addpath=0 rc=$HOME/.bashrc
  if [[ -n $custom ]]; then
    dest=${custom/#\~/$HOME}; dest=$(realpath -ms -- "$dest")
    [[ $dest != *[\'\"\$\`\\]* && $dest != *$'\n'* ]] || { echo "--dir: please use a folder path without quotes, \$, backticks or backslashes"; return 1; }
  fi
  [[ ":$PATH:" == *":$dest:"* ]] || addpath=1
  [[ ${SHELL:-} == */zsh ]] && rc=$HOME/.zshrc

  echo "awake will be installed to: $dest/awake"
  if (( addpath )); then echo "That folder is not on your PATH yet, so one line will be added to ${rc/#$HOME/\~}."
  else echo "That folder is already on your PATH, so no other changes are needed."; fi
  ask "Continue?" || { echo "Cancelled. Nothing was changed. (Use --dir DIR to pick another folder.)"; [[ -n $tmp ]] && rm -f "$tmp"; return 0; }
  mkdir -p "$dest" || { echo "cannot create $dest"; [[ -n $tmp ]] && rm -f "$tmp"; return 1; }
  if (( addpath )); then
    local line="export PATH=\"$dest:\$PATH\" $MARK"
    if ! grep -qxF "$line" "$rc" 2>/dev/null; then
      # replace an older awake PATH line (e.g. a different --dir) instead of stacking them
      if grep -q "$MARK" "$rc" 2>/dev/null; then
        local t2; t2=$(mktemp) || { echo "could not edit $rc"; return 1; }
        grep -v "$MARK" "$rc" > "$t2"; (( $? <= 1 )) && cat "$t2" > "$rc"; rm -f "$t2"
      fi
      # make sure our line starts on its own line, even if the file doesn't end with a newline
      [[ -s $rc && -n $(tail -c1 "$rc") ]] && echo >> "$rc"
      echo "$line" >> "$rc"
    fi
  fi
  install -m 755 "$src" "$dest/awake" || { echo "could not write $dest/awake"; [[ -n $tmp ]] && rm -f "$tmp"; return 1; }
  [[ -n $tmp ]] && rm -f "$tmp"
  echo "installed: $dest/awake"
  if ! { command -v python3 >/dev/null && python3 -I -c 'import gi' 2>/dev/null; }; then
    echo "Note: awake needs python3 with PyGObject. Install it first:"
    echo "  Debian/Ubuntu/Pop!_OS: sudo apt install python3-gi    Fedora: sudo dnf install python3-gobject    Arch: sudo pacman -S python-gobject"
  fi
  echo "Done. Try:  awake 1h"
  (( addpath )) && echo "Open a new terminal first (or run: source ${rc/#$HOME/\~})."
  return 0
}
main "$@"
