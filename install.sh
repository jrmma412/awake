#!/bin/zsh
# Install / uninstall awake.
#   ./install.sh              install the `awake` command
#   ./install.sh --menubar    also add the optional SwiftBar menu bar icon
#   ./install.sh --uninstall  remove everything this script installed
set -u
HERE=${0:A:h}
MARK="# added by awake"
TAG="awake - keep your Mac awake"   # used to make sure we only ever remove our own file

in_path() { [[ ":$PATH:" == *":$1:"* ]]; }
find_installed() {
  for d in /opt/homebrew/bin /usr/local/bin "$HOME/bin"; do
    [[ -f $d/awake ]] && grep -q "$TAG" "$d/awake" 2>/dev/null && { echo "$d/awake"; return; }
  done
}

plugin_dir() {
  local d
  d=$(defaults read com.ameba.SwiftBar PluginDirectory 2>/dev/null) && [[ -n $d ]] && { echo "${d/#\~/$HOME}"; return; }
  echo "$HOME/swiftbar-plugins"
}

case ${1:-} in
  --uninstall)
    bin=$(find_installed)
    [[ -n $bin ]] && "$bin" off >/dev/null 2>&1
    for d in /opt/homebrew/bin /usr/local/bin "$HOME/bin"; do
      [[ -f $d/awake ]] && grep -q "$TAG" "$d/awake" && rm -f "$d/awake" && echo "removed $d/awake"
    done
    p="$(plugin_dir)/awake.5s.sh"
    [[ -e $p ]] && rm -f "$p" && echo "removed $p"
    for f in ~/.zshrc ~/.zprofile; do
      [[ -f $f ]] && grep -q "$MARK" "$f" && { grep -v "$MARK" "$f" > "$f.tmp"; mv "$f.tmp" "$f"; echo "cleaned PATH line in $f"; }
    done
    rm -rf "$HOME/.awake"
    echo "awake uninstalled. (SwiftBar itself, if you installed it, is left alone: brew uninstall --cask swiftbar)"
    exit 0;;
  --menubar|"") ;;
  *) echo "usage: ./install.sh [--menubar | --uninstall]"; exit 1;;
esac

# ---- install the command ----
dest=""
for d in /opt/homebrew/bin /usr/local/bin; do
  if [[ -d $d && -w $d ]] && in_path "$d"; then dest=$d; break; fi
done
if [[ -z $dest ]]; then
  dest=$HOME/bin
  mkdir -p "$dest"
  line="export PATH=\"\$HOME/bin:\$PATH\" $MARK"
  for f in ~/.zshrc ~/.zprofile; do
    grep -q "$MARK" "$f" 2>/dev/null || echo "$line" >> "$f"
  done
  NEEDS_RELOAD=1
fi
install -m 755 "$HERE/awake" "$dest/awake" || { echo "could not write $dest/awake"; exit 1; }
echo "installed: $dest/awake"

# ---- optional menu bar icon ----
if [[ ${1:-} == --menubar ]]; then
  if [[ ! -d /Applications/SwiftBar.app && ! -d ~/Applications/SwiftBar.app ]]; then
    if command -v brew >/dev/null; then
      echo "installing SwiftBar (menu bar host app) with Homebrew..."
      brew install --cask swiftbar || { echo "SwiftBar install failed; install it from https://swiftbar.app and re-run"; exit 1; }
    else
      echo "SwiftBar is not installed. Get it from https://swiftbar.app, then re-run: ./install.sh --menubar"; exit 1
    fi
  fi
  pd=$(plugin_dir); mkdir -p "$pd"
  sed "s|@AWAKE@|$dest/awake|g" "$HERE/menubar/awake.5s.sh" > "$pd/awake.5s.sh"
  chmod +x "$pd/awake.5s.sh"
  echo "installed menu bar plugin: $pd/awake.5s.sh"
  open -a SwiftBar 2>/dev/null
  echo "If SwiftBar asks for a plugin folder, choose: $pd"
fi

echo
echo "Done. Try:  awake 1h"
[[ ${NEEDS_RELOAD:-0} == 1 ]] && echo "(Open a new Terminal tab first, or run: source ~/.zshrc)"
exit 0
