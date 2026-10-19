#!/bin/zsh
# Install / uninstall awake.
#   ./install.sh              install the `awake` command
#   ./install.sh --uninstall  remove it
# Also works piped from the web (public repo):  curl -fsSL <raw install.sh url> | zsh
set -u
MARK="# added by awake"
TAG="awake - keep your Mac awake"
RAW=https://raw.githubusercontent.com/jrmma412/awake/main/awake
in_path() { [[ ":$PATH:" == *":$1:"* ]]; }

if [[ ${1:-} == --uninstall ]]; then
  for d in /opt/homebrew/bin /usr/local/bin "$HOME/bin"; do
    [[ -f $d/awake ]] && grep -q "$TAG" "$d/awake" && { "$d/awake" off >/dev/null 2>&1; "$d/awake" menubar off >/dev/null 2>&1; rm -f "$d/awake"; echo "removed $d/awake"; }
  done
  for f in ~/.zshrc ~/.zprofile; do
    [[ -f $f ]] && grep -q "$MARK" "$f" && { grep -v "$MARK" "$f" > "$f.tmp"; mv "$f.tmp" "$f"; echo "cleaned PATH line in $f"; }
  done
  rm -rf "$HOME/.awake"; echo "awake uninstalled."; exit 0
fi
[[ -z ${1:-} ]] || { echo "usage: ./install.sh [--uninstall]"; exit 1; }

# Use the awake file next to this script if there is one, otherwise download it.
src=${0:A:h}/awake
if [[ ! -f $src ]]; then
  src=$(mktemp) && curl -fsSL "$RAW" -o "$src" || { echo "download failed"; exit 1; }
fi
grep -q "$TAG" "$src" || { echo "unexpected file, aborting"; exit 1; }

dest=""
for d in /opt/homebrew/bin /usr/local/bin; do
  [[ -d $d && -w $d ]] && in_path "$d" && { dest=$d; break; }
done
if [[ -z $dest ]]; then
  dest=$HOME/bin; mkdir -p "$dest"
  for f in ~/.zshrc ~/.zprofile; do
    grep -q "$MARK" "$f" 2>/dev/null || echo "export PATH=\"\$HOME/bin:\$PATH\" $MARK" >> "$f"
  done
  reload=1
fi
install -m 755 "$src" "$dest/awake" || { echo "could not write $dest/awake"; exit 1; }
echo "installed: $dest/awake"
echo "Done. Try:  awake 1h     (optional menu bar icon: awake menubar)"
[[ ${reload:-0} == 1 ]] && echo "Open a new Terminal tab first (or run: source ~/.zshrc)."
exit 0
