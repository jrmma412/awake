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
```

## Install

Paste this into Terminal (it uses the GitHub CLI, so it also works while the
repo is private):

```
d=$(mktemp -d) && gh repo clone jrmma412/awake "$d" -- --depth 1 && "$d/install.sh"
```

Once the repo is public, no GitHub login is needed:

```
d=$(mktemp -d) && git clone --depth 1 https://github.com/jrmma412/awake "$d" && "$d/install.sh"
```

Open a new Terminal tab and type `awake`. That's it. The installer puts `awake`
in `/opt/homebrew/bin` or `/usr/local/bin` when it can write there (so it's
already on your PATH, like `caffeinate`); otherwise it uses `~/bin` and adds
that to your PATH for you.

**Update:** run the install command again.
**Uninstall:** `$d/install.sh --uninstall` from a fresh clone, or just delete the
`awake` file and the `~/.awake` folder.

## Optional: menu bar icon

Not installed by default. To add a ☕ / 💤 icon in the menu bar with
one-click on/off and 30m / 1h / 2h timers, run the installer with `--menubar`:

```
d=$(mktemp -d) && gh repo clone jrmma412/awake "$d" -- --depth 1 && "$d/install.sh" --menubar
```

This uses [SwiftBar](https://swiftbar.app) (installed with Homebrew if you have
it). If SwiftBar asks for a plugin folder, pick the one the installer prints
(`~/swiftbar-plugins`). The icon is experimental.

## What it does

- Runs `caffeinate -dimsu` (display, idle, disk, system on AC, user-active).
- Sets the screen saver idle time to 0 and remembers the previous value.
- `awake off` (or the timer ending) restores it. If you never had a custom
  value, the setting is deleted on restore rather than overwritten with a guess.
- State lives in `~/.awake` (user-only, mode 700).

Verified on macOS (Apple Silicon): `pmset -g assertions` shows the caffeinate
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
  restarts `cfprefsd` so it takes effect. No sudo, no network requests.
  The installer only writes the `awake` file, an optional PATH line (tagged
  `# added by awake`) in `~/.zshrc`/`~/.zprofile`, and the optional plugin.

## License

MIT, see [LICENSE](LICENSE).
