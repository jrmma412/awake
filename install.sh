#!/bin/zsh
# Install / uninstall awake.
#   ./install.sh              install the `awake` command
#   ./install.sh --uninstall  remove it
# Also works piped from the web (public repo):
#   curl -fsSL https://raw.githubusercontent.com/jrmma412/awake/main/install.sh | zsh
# (to uninstall that way:  ... | zsh -s -- --uninstall)
main() {
  local MARK="# added by awake" TAG="awake - keep your Mac awake"
  local REF=v1.2.0   # release the downloaded copy is pinned to
  local RAW=https://raw.githubusercontent.com/jrmma412/awake/$REF/awake
  local d f

  if [[ ${1:-} == --uninstall ]]; then
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
        local t; t=$(mktemp) && grep -v "$MARK" "$f" > "$t"; cat "$t" > "$f"; rm -f "$t"   # in place: keeps symlinks/permissions
        echo "cleaned PATH line in $f"
      fi
    done
    if (( found )) || [[ ! -s $HOME/.awake/idleTime ]]; then rm -rf "$HOME/.awake"
    else echo "kept ~/.awake (it holds your saved screen saver setting); run 'awake off' first, then delete it"; fi
    echo "awake uninstalled."; return 0
  fi
  [[ -z ${1:-} ]] || { echo "usage: install.sh [--uninstall]"; return 1; }

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
  for d in /opt/homebrew/bin /usr/local/bin; do
    [[ -d $d && -w $d && ":$PATH:" == *":$d:"* ]] || continue
    if [[ -L $d/awake ]]; then echo "$d/awake is managed by Homebrew; use: brew upgrade awake"; [[ -n $tmp ]] && rm -f "$tmp"; return 0; fi
    dest=$d; break
  done
  local reload=0
  if [[ -z $dest ]]; then
    dest=$HOME/bin; mkdir -p "$dest"
    grep -q "$MARK" ~/.zshrc 2>/dev/null || echo "export PATH=\"\$HOME/bin:\$PATH\" $MARK" >> ~/.zshrc
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
