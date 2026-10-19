#!/bin/zsh
# Install / uninstall awake.
#   ./install.sh              install the `awake` command
#   ./install.sh --uninstall  remove it
#   options: -y / --yes  don't ask, use the default location
#            --dir DIR   install into DIR instead of the automatic choice
#   piped:   curl ... | zsh -s -- -y      (options go after "zsh -s --")
# Also works piped from the web (public repo):
#   curl -fsSL https://raw.githubusercontent.com/jrmma412/awake/main/install.sh | zsh
# (to uninstall that way:  ... | zsh -s -- --uninstall [--all] [-y])
main() {
  local MARK="# added by awake" TAG="awake - keep your Mac awake"
  local REF=v1.2.4   # release the downloaded copy is pinned to
  local RAW=https://raw.githubusercontent.com/jrmma412/awake/$REF/awake
  local d f yes=0 custom=""
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
    local a; read -r "a?$1 [Y/n] " </dev/tty
    [[ -z $a || $a == [Yy]* ]]
  }

  if [[ ${1:-} == --uninstall ]]; then
    # Prefer the installed awake's own uninstaller (it also handles --all).
    shift
    local b; b=$(command -v awake 2>/dev/null)
    if [[ -n $b ]] && grep -q "uninstall()" "${b:A}" 2>/dev/null; then
      if (( yes )); then "$b" uninstall -y "$@"; else "$b" uninstall "$@"; fi
      return
    fi
    local found=0
    for d in /opt/homebrew/bin /usr/local/bin "$HOME/bin"; do
      if [[ -L $d/awake ]]; then
        echo "$d/awake is managed by Homebrew; use: brew uninstall awake"
      elif [[ -f $d/awake ]] && grep -q "$TAG" "$d/awake"; then
        "$d/awake" off >/dev/null 2>&1; "$d/awake" menubar off >/dev/null 2>&1
        rm -f "$d/awake"; echo "removed $d/awake"; found=1
      fi
    done
    for f in ~/.zshrc ~/.zprofile; do
      if [[ -f $f ]] && grep -q "$MARK" "$f"; then
        local t; t=$(mktemp) || { echo "could not edit $f; remove the line ending in '$MARK' yourself"; continue; }
        grep -v "$MARK" "$f" > "$t"
        if (( $? <= 1 )); then cat "$t" > "$f" && echo "cleaned PATH line in $f"   # in place: keeps symlinks/permissions
        else echo "could not edit $f; remove the line ending in '$MARK' yourself"; fi
        rm -f "$t"
      fi
    done
    if (( found )) || [[ ! -s $HOME/.awake/idleTime ]]; then rm -rf "$HOME/.awake"
    else echo "kept ~/.awake (it holds your saved screen saver setting); run 'awake off' first, then delete it"; fi
    echo "awake uninstalled."; return 0
  fi

  # Use the awake file next to this script only when run as a file (./install.sh).
  # When piped (curl | zsh) there is no script file, so always download.
  local src=""
  [[ -n ${ZSH_SCRIPT:-} && -f ${ZSH_SCRIPT:A:h}/awake ]] && src=${ZSH_SCRIPT:A:h}/awake
  local tmp=""
  if [[ -z $src ]]; then
    tmp=$(mktemp) && curl -fsSL "$RAW" -o "$tmp" || { echo "download failed"; rm -f "$tmp"; return 1; }
    src=$tmp
  fi
  grep -q "$TAG" "$src" || { echo "unexpected file, aborting"; [[ -n $tmp ]] && rm -f "$tmp"; return 1; }

  # Prefer a folder already on PATH that we can write to (no PATH edit needed).
  local dest=""
  if [[ -n $custom ]]; then
    dest=${custom/#\~/$HOME}; dest=${dest:a}
    [[ $dest != *[\'\"\$\`\\]* && $dest != *$'\n'* ]] || { echo "--dir: please use a folder path without quotes, \$, backticks or backslashes"; return 1; }
  fi
  for d in /opt/homebrew/bin /usr/local/bin; do
    [[ -z $dest ]] || break
    [[ -d $d && -w $d && ":$PATH:" == *":$d:"* ]] || continue
    if [[ -L $d/awake ]]; then echo "$d/awake is managed by Homebrew; use: brew upgrade awake"; [[ -n $tmp ]] && rm -f "$tmp"; return 0; fi
    dest=$d; break
  done
  local reload=0 addpath=0
  if [[ -z $dest ]]; then dest=$HOME/bin; fi
  if [[ ":$PATH:" != *":$dest:"* ]]; then addpath=1; fi

  echo "awake will be installed to: $dest/awake"
  if (( addpath )); then echo "That folder is not on your PATH yet, so one line will be added to ~/.zshrc."
  else echo "That folder is already on your PATH, so no other changes are needed."; fi
  ask "Continue?" || { echo "Cancelled. Nothing was changed. (Use --dir DIR to pick another folder.)"; [[ -n $tmp ]] && rm -f "$tmp"; return 0; }
  mkdir -p "$dest" || { echo "cannot create $dest"; [[ -n $tmp ]] && rm -f "$tmp"; return 1; }
  if (( addpath )); then
    local line="export PATH=\"$dest:\$PATH\" $MARK"
    if ! grep -qxF "$line" ~/.zshrc 2>/dev/null; then
      # replace an older awake PATH line (e.g. a different --dir) instead of stacking them
      if grep -q "$MARK" ~/.zshrc 2>/dev/null; then
        local t2; t2=$(mktemp) || { echo "could not edit ~/.zshrc"; return 1; }
        grep -v "$MARK" ~/.zshrc > "$t2"; (( $? <= 1 )) && cat "$t2" > ~/.zshrc; rm -f "$t2"
      fi
      # make sure our line starts on its own line, even if .zshrc doesn't end with a newline
      [[ -s ~/.zshrc && $(tail -c1 ~/.zshrc) != "" ]] && echo >> ~/.zshrc
      echo "$line" >> ~/.zshrc
    fi
    reload=1
  fi
  install -m 755 "$src" "$dest/awake" || { echo "could not write $dest/awake"; [[ -n $tmp ]] && rm -f "$tmp"; return 1; }
  [[ -n $tmp ]] && rm -f "$tmp"
  echo "installed: $dest/awake"
  echo "Done. Try:  awake 1h     (optional menu bar icon: awake menubar)"
  (( reload )) && echo "Open a new Terminal tab first (or run: source ~/.zshrc)."
  return 0
}
main "$@"
