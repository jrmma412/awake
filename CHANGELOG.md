# Changelog

## Unreleased

Linux only: the macOS script, installer and Homebrew formula are unchanged.

### Added
- Linux `awake display [on [WIDTHxHEIGHT]|off|status]` (was "macOS-only"): a virtual display from
  the Linux kernel's `vkms` driver, for a PC used with no monitor or with the monitor off
  (Moonlight/Sunshine, remote desktop), instead of an HDMI dummy plug.
  - Not set up: prints the one command that loads `vkms` at every boot
    (`echo vkms | sudo tee /etc/modules-load.d/awake-vdisplay.conf`), then restart.
  - Loaded, on COSMIC: sets it to 1920x1080 while it still has the driver's own default size
    (1024x768), or to the size given, using `cosmic-randr mode` with the highest refresh COSMIC
    offers for that size. COSMIC remembers it. A size it doesn't offer prints the sizes it does.
  - Other desktops, or no desktop to talk to: reports the display from `/sys/class/drm`, and says to
    set its size in the display settings.
  - Run from SSH: finds the desktop's Wayland socket in `$XDG_RUNTIME_DIR`.
  - `off` prints how to remove it (`sudo rm` of the file, then restart). It never deletes a shared
    file: if another file loads `vkms`, it says to remove that line.
  - `awake status` shows a `display:` line once it's set up. `awake uninstall` keeps the boot file
    and prints how to remove it.

### Decisions
- awake never runs `sudo` (as with `awake clamshell` and the jiggle setup): it prints the command.
- Set up for the next boot rather than `sudo modprobe vkms` into the running desktop, so COSMIC
  starts with the display instead of having it added while running.
- awake never switches the virtual display on or off itself (no `cosmic-randr enable/disable`). In
  testing, `disable` followed within a second by `enable` deadlocked cosmic-comp: its main thread
  and the DP-3 render thread both waited forever, the desktop froze, and only a restart fixed it
  (it looks like pop-os/cosmic-comp#2693). If it's turned off in COSMIC's settings,
  `awake display` says so and leaves turning it back on to you.
- `off` doesn't hide the display right away, for the same reason; it says how to remove the driver
  setting and that the display settings can hide it until then.
- COSMIC has no virtual outputs of its own yet (its screen-sharing portal offers no virtual
  source; pop-os/cosmic-comp#2878 is only a prototype), and NVIDIA's driver ignores the kernel's
  EDID override, so `vkms` is the only way on this hardware.

### Testing status
- pytest on Linux: 79 passed, 15 skipped (macOS-only). New display tests run with a fake
  `/sys/class/drm`, `/sys/module/vkms`, `modules-load.d` folder and `cosmic-randr`. They cover:
  - not set up, and set up but waiting for the restart
  - setting 1920x1080 from the driver default, and keeping a size you chose
  - asking for a size, including one it doesn't offer
  - turned off in COSMIC
  - `off`, including a shared file that also loads `vkms`
  - another desktop, COSMIC not answering, finding the desktop from SSH, the driver loaded with no
    display, and bad arguments
  - every test checks that `sudo` never ran, and none switch the display on or off
- Every test file change compiles on Python 3.9.
- A run with five deliberate bugs in the script: each one made at least one test fail.
- Live on Pop!_OS 24.04 (COSMIC, NVIDIA RTX 3080, one monitor on DP-3), with
  `sudo modprobe vkms` in the running desktop:
  - COSMIC added `Virtual-1` at 1024x768 to the right of the monitor, with wallpaper, panel and dock.
  - `cosmic-randr mode Virtual-1 1920 1080` worked.
  - Capturing it (ext-image-copy-capture) returned full frames in about 10-20 ms.
  - It cost cosmic-comp about 2% of one CPU core.
  - Then the freeze described under Decisions.
- Not tested: the new script on the real desktop, loading `vkms` at boot, running with no monitor,
  streaming it with Sunshine, GNOME and KDE.

## 1.12.0 (2026-11-22)

Linux catch-up: the macOS changes from 1.9.0 to 1.11.0, ported to and tested on Linux. No change
to the macOS script apart from its version number.

### Added
- Linux `awake clamshell` (was "macOS-only"): shows the power source, whether there is a lid and
  whether it's closed, what closing it does right now and on battery / plugged in / with 2+ displays
  or docked (logind's `HandleLidSwitch`, `HandleLidSwitchExternalPower`, `HandleLidSwitchDocked`
  and `Docked`), and which program has taken the lid over from logind, if any (KDE's PowerDevil,
  GNOME's gsd-power while an external monitor is attached). Prints the `sudo` commands to add
  `/etc/systemd/logind.conf.d/awake-lid.conf` (`HandleLidSwitchExternalPower=lock`,
  `HandleLidSwitchDocked=ignore`) and to undo it; if the file is there but logind isn't using it,
  says so and prints the reload command instead. Only reads (`busctl get-property` with
  `--auto-start=no`, `ListInhibitors`); never runs sudo. On a desktop PC it says there's no lid.
- Linux `awake status` adds a reminder line while `awake-lid.conf` exists (as macOS does for
  `pmset disablesleep`), and says when it exists but isn't in effect.
- Linux `awake uninstall` lists the lid setting as something it keeps, with the command to remove it.

### Changed
- Linux `awake status` now always exits 0 (it exited 1 whenever jiggle was off; macOS was fixed in 1.11.0).
- Linux `awake all off` matches macOS: says agent mode had nothing to stop when it was never
  installed, and ends with `awake all: everything is off`. Unlike macOS, it only says that when
  every part did stop; otherwise it says so and exits 1.
- Linux help lists `awake clamshell` and `awake all random [time]`.

### Decisions
- The Linux lid command only covers "plugged in" and "with 2+ displays". On battery the
  lid still suspends, so a laptop in a bag doesn't run flat. Plugged in, the lid locks the
  screen (`lock`) rather than doing nothing (`ignore`).
- Which lid locks count follows logind's rule: a lock is skipped only when its process is in a
  login session that isn't active (checked with `loginctl show-session N -p Active`). A process
  outside any session, such as a desktop's user service, always counts, whoever owns it. When the
  lock's "who" is just the user's name (GNOME does this), the program is named from
  `/proc/PID/comm` instead.
- `awake display` stays macOS-only: vdisplay is a macOS tool. The SwiftBar auto-open (1.9.0)
  doesn't apply, since Linux has no menu bar icon.

### Review
- Independent review before release. Fixed from it:
  - The printed command block failed when pasted (a note on the reload line was a bash syntax
    error), and `status` then claimed the lid setting was in effect.
  - GNOME's lock showed the user's name instead of the program's.
  - The docked / 2+ displays case was missing.
  - `all off` always said "everything is off".
  - A test read the real `/etc`, so it failed on a laptop that already has the setting.
  - Reading UPower could start the service.
- A second review round fixed:
  - The tests needed Python 3.12. A backslash inside an f-string expression meant the file
    wouldn't even load on 3.9 to 3.11, which took the macOS tests down too. Checked: it now
    compiles on Python 3.9.
  - The lock filter went by user id instead of logind's session rule.
  - KDE's name was cut to 15 characters.
  - An unknown power source was shown as "on battery".
  - The battery/lid-closed test could pass with the feature broken.

### Testing status
- pytest on Linux: 60 passed, 15 skipped (macOS-only). New tests:
  - clamshell with a fake `busctl`: no lid; lid suspends, where the printed commands must parse as
    bash and the printf must write exactly the intended file; already kept running; file present
    but not in effect; battery with the lid closed; docked; unknown power source; logind not
    answering; GNOME, using a real process named `gsd-power`; KDE's full name kept; another user's
    lock from outside a session counts; bad argument; never calls sudo
  - the status reminder and exit code
  - the uninstall note
  - `all off` without agent mode, and while busy
  - bad jiggle/all arguments
- Live on Pop!_OS 24.04, COSMIC (desktop PC, no lid):
  - jiggle: simple, then the already-on hint, random, a bad argument (left running), `simple 2m`, off
  - `all random 3m`: COSMIC's suspend setting went to never, and `all off` restored it to 2h
  - `all simple` while already on; `all off` twice; `clamshell` ("no lid")
- Not tested on a real Linux laptop: the lid cases were checked only with fake logind/UPower answers.

### Open
- macOS `awake all off` still says "everything is off" even when a part failed (Linux fixed here).

## 1.11.0 (2026-11-14)

### Added
- `awake clamshell` (macOS): shows the power source, whether the lid is closed, whether
  closing it would sleep the Mac (`AppleClamshellCausesSleep` from IOPMrootDomain), and
  whether `pmset disablesleep` is on. Prints the exact `sudo pmset -a disablesleep 1/0`
  command for you to run. It only reads (`ioreg`, `pmset -g`) and never runs sudo.
  Prompted by the clamshell MacBook Pro setup: `awake agent` (caffeinate) can't stop
  lid-close sleep, so this explains what can. Pairs with the new vdisplay tool.
- `awake status` adds a reminder line while system sleep is disabled.
- Linux: `awake clamshell` says it's macOS-only and points to `HandleLidSwitch` in logind.conf.
- `awake display [on|off|status]` (macOS): optional virtual-display add-on using the separate
  vdisplay tool (jrmma412/homebrew-vdisplay). Installs it with Homebrew after asking, starts
  it now and at login through `brew services`, and removes it with `off`. `awake status`,
  `awake clamshell` and the menu bar icon show it (with an add/remove menu item) only when
  vdisplay is installed. `awake uninstall` leaves vdisplay installed. Linux says it's macOS-only.

### Changed
- macOS `awake status` now always exits 0. Before, it exited 1 whenever jiggle was off,
  which was a side effect of its last line rather than intended.

### Testing status
- Logic checked with fake `ioreg`/`pmset` output for all four states (sleep enabled with lid
  sleep, display attached, disabled on battery, flag missing so it falls back to `pmset -g`).
  New pytest tests on the macOS CI runner confirm it never calls sudo and only calls `pmset -g`.
  On the real MacBook (M2 Pro, macOS 26.5.1): `awake clamshell` correctly reported the lid closed
  and no lid sleep while the monitors were attached. `awake display status`, `awake status`,
  `awake clamshell` and the menu all showed the running virtual display (id 17). Not yet run
  on the real Mac: `awake display` installing vdisplay and turning it on or off.

## 1.10.0 (2026-11-13)

### Added
- `awake all [simple|random] [time]` (also `all on random`): turn everything on with the chosen
  jiggle mode in one command; works when already on (it switches the running jiggle). Prompted
  by `all on && jiggle random` failing with "already on" on the work Mac, which was still on a
  pre-1.9.0 script. Bad modes print usage. Applied to `awake` and `linux/awake`; README and help
  updated.

### Testing status
- Verified live on macOS: all simple, all on random, all random, bad argument. Not tested: the
  Linux script (same change; no tests cover jiggle).

## 1.9.0 (2026-11-11)

### Changed
- macOS: the menu bar icon comes back by itself. Any awake command opens SwiftBar if the icon is
  installed but SwiftBar isn't running (not for `menubar`, `uninstall` or internal commands, so
  "Hide icon until next login" still works). The agent LaunchAgent also opens SwiftBar at login.
  Re-run `awake agent` once to pick up the new LaunchAgent. (PR #2) README updated.
- `awake jiggle simple|random [time]` switches mode when jiggle is already on, instead of
  refusing with "already on". A time can be given at the same time (`random 2h`).
- Plain `awake jiggle` / `jiggle on` / `all on` while jiggle is already on changes nothing and
  prints a hint about `simple`, `random` and `off`.
- `awake all off` skips `agent off` when agent mode was never installed (prints an
  informational line) and ends with `awake all: everything is off`.
- Applied to both `awake` (macOS) and `linux/awake`; README and `--help` text updated.

### Added
- `awake jiggle simple` (alias `normal`): names the default 1-pixel nudge. `jiggle`,
  `jiggle on` and `all` still start it.

### Decisions
- `awake jiggle off` turns jiggle fully off. It does not fall back to simple mode.
- A bad argument (e.g. `jiggle bogus`) prints usage and leaves a running jiggle alone; the
  switch only happens after the arguments parse.

### Testing status
- `zsh -n awake` and `bash -n linux/awake` pass; pytest 7 passed, 37 skipped (no existing
  test covers jiggle).
- Mode switching verified live on macOS (random -> simple -> random, bare `jiggle` while on,
  bad argument).
- **Not tested:** the Linux script's mode switching. No tests were added for the new behavior.

### Open / not done
- Installed Homebrew copy was 1.7.0 when checked (repo is 1.8.0); not upgraded.
- Release steps for the eventual version: bump `VERSION` in `awake` and `linux/awake`, then
  pin `Formula/awake.rb` and `install.sh`, tag, and release (as in earlier releases).
