# awake

Keep your Mac awake with the screen on, straight from Terminal. Like
`caffeinate`, but it also turns off the screen saver while it's running and puts
your setting back when it stops.

```
awake            # on until you turn it off
awake 2h         # on for 2 hours (also 30m, 1h30m, 90 = seconds)
awake off        # off, screen saver setting restored
awake toggle     # flip on/off
awake status     # on or off, and time left
awake help       # all commands
```

(`awake on 2h` also works. If it's already on, a new time is ignored: run
`awake off` first.)

## Install

**Homebrew (easiest):**

```
brew tap jrmma412/awake https://github.com/jrmma412/awake
brew install jrmma412/awake/awake
```

**Or one line, no Homebrew needed:**

```
curl -fsSL https://raw.githubusercontent.com/jrmma412/awake/main/install.sh | zsh
```

The installer tells you where it will put `awake` and asks before doing anything
(add `-y` to skip the question, or `--dir ~/somewhere` to choose the folder).

Then open a new Terminal tab. `awake` works from any folder, like `caffeinate`.
The installer puts it in `/opt/homebrew/bin` or `/usr/local/bin` when it can
(already on your PATH); otherwise in `~/bin`, and adds that to your PATH.
Find it any time with `command -v awake`.

Pick one install method. If you switch to Homebrew, uninstall the other first.

**Update:** `brew upgrade awake`, or run the install line again.
**Uninstall:**

```
awake uninstall          # remove awake, its PATH line and its settings
awake uninstall --all    # same, plus the menu bar icon's SwiftBar app and its settings
```

It shows what it will remove and asks first (`-y` skips the question). Your
screen saver setting is restored before anything is deleted.

## Optional: menu bar icon

Not installed by default. One extra command adds a ☕ / 💤 icon in the menu bar
with one-click on/off and 30m / 1h / 2h timers:

```
awake menubar          # add it
awake menubar off      # remove it
```

**This uses a separate app, [SwiftBar](https://swiftbar.app)** (free, open
source), to draw the icon. The `awake` command itself does not need it.

- If SwiftBar isn't installed, `awake menubar` asks before installing it with
  Homebrew (`brew install --cask swiftbar`, which also runs a normal Homebrew
  update). Without Homebrew it tells you where to download SwiftBar.
- If SwiftBar has no plugin folder yet, `awake` sets it to `~/swiftbar-plugins`
  for you, so there's nothing to choose. If you already use SwiftBar, your
  existing plugin folder is kept and the icon is added there.
- `awake menubar off` removes only the awake icon. SwiftBar stays installed;
  remove it with `brew uninstall --cask swiftbar` if you don't use it for
  anything else.

## What it does

- Runs `caffeinate` with display, idle, disk and system (on AC) assertions; with a timer it also declares the user active (`-u`).
- Sets the screen saver idle time to 0 and remembers the previous value.
- `awake off` (or the timer ending) restores it. If you never had a custom
  value, the setting is deleted on restore rather than overwritten with a guess.
- State lives in `~/.awake` (user-only, mode 700).

Verified on macOS (Apple Silicon; Intel not tested): `pmset -g assertions` shows the caffeinate
assertions while on, and the screen saver time is restored after the timer ends
or on `awake off`.

## Security notes

- While `awake` is on, the screen saver (and any "require password after screen
  saver" lock that depends on it) won't start. Turn it off when you walk away.
- If the Mac reboots or the process is killed while on, `awake status` reports
  the leftover state, and `awake off` (or the next `awake`) restores the
  original screen saver time instead of overwriting it.
- Times are strictly validated and passed to the background process as
  arguments, never spliced into a command string, so input can't inject commands.
- The pid file is only trusted if it holds a number and that process is really
  `caffeinate`.
- It changes one user-level preference (`com.apple.screensaver idleTime`) and
  restarts `cfprefsd` so it takes effect. No sudo. The `awake` command itself makes
  no network requests (`awake menubar` may run `brew install --cask swiftbar`).
  The installer only writes the `awake` file and, if needed, a PATH line (tagged
  `# added by awake`) in `~/.zshrc`. `awake menubar` writes one
  plugin file.

## License

MIT, see [LICENSE](LICENSE).
