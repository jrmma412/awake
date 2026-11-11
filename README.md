# awake

Keep your Mac awake with the screen on, straight from Terminal. Like
`caffeinate`, but it also turns off the screen saver while it's running and puts
your setting back when it stops.

**Also for Linux** (same commands): see [Linux](#linux) below. Everything else in
this README describes the macOS version.

```
awake            # on until you turn it off
awake 2h         # on for 2 hours (also 30m, 1h30m, 90 = seconds)
awake off        # off, screen saver setting restored
awake until 5pm  # on until a clock time (5:30pm, 17:30; tomorrow if already past)
awake toggle     # flip on/off
awake status     # on or off, and time left
awake all        # everything: keep awake + jiggle + agent mode
awake jiggle     # (optional) nudge the mouse so chat apps don't show you away
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

The installer tells you where it will put `awake` and asks before doing anything.
To skip the question or pick the folder, add options after `zsh -s --`, e.g.
`curl -fsSL …/install.sh | zsh -s -- -y` or `… | zsh -s -- --dir ~/somewhere`.

Then open a new Terminal tab. `awake` works from any folder, like `caffeinate`.
The installer puts it in `/opt/homebrew/bin` or `/usr/local/bin` when it can
(already on your PATH); otherwise in `~/bin`, and adds that to your PATH.
Find it any time with `command -v awake`.

Pick one install method. If you switch to Homebrew, uninstall the other first.
If you remove it with plain `brew uninstall awake`, run `awake off` first so your
screen saver setting is restored (`awake uninstall` does this for you).

**Update:** `brew upgrade awake`, or run the install line again.
**Uninstall:**

```
awake uninstall          # remove awake, its PATH line and its settings
awake uninstall --all    # same, plus the menu bar icon's SwiftBar app and its settings
```

It shows what it will remove and asks first (`-y` skips the question). Your
screen saver setting is restored before anything is deleted.

## Until a clock time

Instead of a duration, give a time of day:

```
awake until 5pm              # also 5:30pm, 5:30 pm, 17:30
awake jiggle until 5pm       # works with jiggle...
awake all until 9am          # ...and with all
```

- If that time has already passed today, it means tomorrow (awake says so).
- A bare `5` is rejected as ambiguous: write `5pm` or `17:00`.
- `awake status` shows the time left and the end time.
- Agent mode has no timer, so in `awake all until 5pm` the timer covers keep-awake and jiggle only.

## Optional: menu bar icon

Not installed by default. One extra command adds a ☕ / 💤 icon in the menu bar
with one-click on/off and 30m / 1h / 2h timers:

```
awake menubar          # add it
awake menubar quit     # hide it until next login
awake menubar off      # remove it
```

The icon's own menu has the same two options at the bottom (**Hide icon until next
login** and **Remove menu bar icon**), so you can get rid of it without Terminal.
If the icon is installed but SwiftBar isn't running, any `awake` command opens SwiftBar again
(except `awake menubar ...` and `uninstall`, so hiding still works). With agent mode on, SwiftBar
also opens at login (run `awake agent` once after upgrading to 1.9.0 to pick this up).
Removing it also quits SwiftBar if awake was its only plugin. Upgrading awake
updates the menu automatically (if you added the icon before 1.3.1, run
`awake menubar` once to switch to the self-updating version).

**This uses a separate app, [SwiftBar](https://swiftbar.app)** (free, open
source), to draw the icon. The `awake` command itself does not need it.

- If SwiftBar isn't installed, `awake menubar` asks before installing it with
  Homebrew (`brew install --cask swiftbar`, which also runs a normal Homebrew
  update). Without Homebrew it tells you where to download SwiftBar. In a
  script (no terminal to ask), set `AWAKE_YES=1` to allow the install.
- If SwiftBar has no plugin folder yet, `awake` sets it to `~/swiftbar-plugins`
  for you, so there's nothing to choose. If you already use SwiftBar, your
  existing plugin folder is kept and the icon is added there.
- `awake uninstall --all` removes SwiftBar too, unless you have other SwiftBar
  plugins, in which case SwiftBar is left alone.
- `awake menubar off` removes only the awake icon (and quits SwiftBar if nothing
  else uses it). SwiftBar stays installed and may reopen at login; remove it with
  `brew uninstall --cask swiftbar` if you don't use it for anything else.

## Optional: mouse jiggle

`awake jiggle random [time]` is a variant: after a varied 20-75 seconds of no input it
glides the pointer along a curved path to a random spot 40-250 pixels away (kept on its
screen; moves only, never clicks). Everything below applies to both; `awake jiggle status`
shows which mode is on and `awake jiggle off` stops either. `awake jiggle simple` is the
default 1-pixel nudge (what `awake jiggle`, `awake jiggle on` and `awake all` start); running
`awake jiggle random` or `awake jiggle simple` while jiggle is already on switches to that mode.

Keeping the Mac awake doesn't stop Teams, Slack or remote-desktop tools from showing
you as "away": they watch for real mouse and keyboard activity. `awake jiggle` nudges
the pointer 1 pixel out and back to look like activity:

```
awake jiggle           # on until you turn it off
awake jiggle 2h        # on for a while (30m, 2h, 1h30m, 90 = seconds)
awake jiggle off       # stop
awake jiggle status    # on or off, and time left
```

- It only nudges after **30 seconds with no mouse or keyboard input**, so it never
  fights you while you are using the Mac. The pointer ends up where it started.
- **Needs the Accessibility permission** (macOS only lets trusted apps send input).
  The first time, `awake jiggle` opens System Settings > Privacy & Security >
  Accessibility; turn it on for your terminal app and run it again.
- Independent of `awake on/off`: it does not keep the Mac awake or touch the screen
  saver by itself, so use both together if you want both. `awake status` shows it and
  `awake uninstall` stops it.
- It stops on restart or logout (it is not a login item).
- **Security:** fake input also keeps the screen saver and any inactivity auto-lock
  from starting, and hides your real idle time from apps. Don't leave it on when you
  walk away, and check your workplace's policy before using it on a work Mac.

## Optional: always-on agent mode

For a Mac that runs background services, bots or AI agents 24/7. Not installed by default:

```
awake agent            # add it (starts now and at every login, and opens the menu bar icon's SwiftBar if installed)
awake agent status     # is it running?
awake agent off        # remove it
```

- Keeps the **system** awake (idle, disk and system-on-AC sleep prevented) so
  network services keep running, and comes back after restarts (a LaunchAgent,
  `~/Library/LaunchAgents/com.jrmma412.awake.agent.plist`, running
  `/usr/bin/caffeinate -ims`).
- Unlike `awake on`, it does **not** keep the display on and does **not** touch the
  screen saver, so the screen still turns off and locks normally. Safer for a Mac
  that is always on.
- Independent of `awake on/off`: you can still use those as usual. `awake status`
  shows agent mode too, and `awake uninstall` removes it.
- On a MacBook, system sleep is only prevented while plugged in (macOS rule for `-s`).

## Everything at once: `awake all`

The three extras are separate, so use any one alone or all together:

```
awake all            # keep awake + mouse jiggle + agent mode ("awake all on" works too)
awake all 2h         # the same; the timer covers keep-awake and jiggle
awake all off        # stop all three
```

- Agent mode has no timer: it stays on (also after restarts) until `awake all off` or
  `awake agent off`.
- `awake all off` always runs all three stops. Agent mode is optional and not installed
  by default, so you will see `agent mode: nothing to stop` if you never ran `awake agent`
  or `awake all`; that is informational, not an error. The last line, `awake all: everything
  is off`, confirms the result.
- If one part can't start (for example jiggle without the Accessibility permission),
  `awake all` says so and the others still run.

## Mix and match

`awake` (keep awake, screen saver off), `awake jiggle` and `awake agent` are three
independent switches. Turn on any combination, and turn each off on its own:

| You want | Run | Turn off |
|---|---|---|
| All three | `awake all` (or `awake all until 5pm`) | `awake all off` |
| Agent + jiggle | `awake agent` then `awake jiggle` (or `awake jiggle 2h`) | `awake jiggle off`, `awake agent off` |
| Keep awake + jiggle, no agent | `awake on jiggle 8h` (or `awake on jiggle until 5pm`, or `awake 2h` then `awake jiggle 2h`) | `awake off`, `awake jiggle off` |
| Jiggle only | `awake jiggle 1h` | `awake jiggle off` |
| Agent only | `awake agent` | `awake agent off` |
| Keep awake only | `awake 2h` | `awake off` |

Run each part as its own command (or chain them: `awake 2h && awake jiggle 2h`).
`awake status` lists every part that is on. Notes:

- Agent mode has no timer; it stays on until `awake agent off`. A time on `awake all`
  covers keep-awake and jiggle only.
- Jiggle also keeps the display on and the screen from locking while it runs, even
  with agent mode (whose own screen otherwise sleeps and locks normally). See jiggle's
  security note.

## Linux

The same `awake` command for Linux desktops, in [`linux/`](linux/). Built and tested on
Pop!_OS 24.04 with COSMIC (Wayland); GNOME and KDE are supported in the code but not yet tested.

**Install** (no sudo; goes to `~/.local/bin`, asks first):

```
curl -fsSL https://raw.githubusercontent.com/jrmma412/awake/main/linux/install.sh | bash
```

Or from a clone: `./linux/install.sh`. Options go after `bash -s --` (`-y`, `--dir DIR`).
**Update:** run the install line again. **Uninstall:** `awake uninstall`.
Needs `python3` with PyGObject (`python3-gi`), which desktop distributions ship by default.

All the commands above work the same (`awake 2h`, `awake until 5pm`, `awake jiggle`,
`awake jiggle random`, `awake agent`, `awake all`, `awake status`, ...). What differs:

- **Keep awake** asks the desktop not to blank the screen, lock or suspend (the request a
  video player makes: `org.freedesktop.ScreenSaver`, GNOME's session manager, KDE's power
  management) and takes a systemd sleep lock. No setting is changed, so there is nothing to
  restore: when awake stops for any reason (off, timer, crash, reboot) your normal settings apply.
- **Jiggle** moves the pointer with a virtual mouse (`/dev/uinput`), the only way to do it on
  Wayland, and only when the desktop reports you idle (Wayland idle notifications, or GNOME's
  idle monitor). You need permission to use `/dev/uinput`: Steam's controller support already
  grants it; otherwise `awake jiggle` prints the one-time `sudo` command. On a desktop that
  can't report idle time, plain jiggle nudges every 30s regardless and `jiggle random` is refused.
  `jiggle random` uses relative moves, so the distance varies with your pointer speed setting.
- **Agent mode** on COSMIC sets "suspend when plugged in" to never (the same setting as
  Settings > Power) and remembers your previous value; `awake agent off` puts it back, unless
  you changed it yourself in the meantime. COSMIC needs this because its only "don't suspend"
  request also keeps the screen on. On other desktops it is a systemd user service
  (`awake-agent.service`) holding suspend-only requests; it starts at login
  (`sudo loginctl enable-linger $USER` to run with nobody logged in). On battery, normal
  suspend still applies on COSMIC.
- **No menu bar icon yet** (`awake menubar` is macOS-only for now).
- **Security:** the same notes apply (no auto-lock while on; jiggle hides your idle time).
  `/dev/uinput` access lets any program you run create virtual input devices.

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
  `# added by awake`) in `~/.zshrc`. `awake menubar` writes one plugin file
  and, only if SwiftBar has no plugin folder yet, sets SwiftBar's
  `PluginDirectory` preference.
- If macOS refuses to restore the screen saver setting, `awake` keeps the saved
  value and tells you, so `awake off` can try again; it never throws it away.
- `awake jiggle` sends synthetic mouse-move events (1 pixel, out and back, only after 30s of no
  input) and needs the Accessibility permission for your terminal app; see the security note in its section.
- On a Mac where an administrator manages the screen saver (e.g. a work
  profile), `awake` warns that the screen saver may still start.

## License

MIT, see [LICENSE](LICENSE).
