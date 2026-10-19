# awake

A tiny zsh command for macOS that keeps the Mac awake with the screen on.

## Usage

```
awake on [seconds]   # keep display/system awake; optional timer in whole seconds
awake off            # stop and restore the previous screen saver setting
awake status         # show whether it is on
```

## What it does

- Runs `caffeinate -dimsu` (display, idle, disk, system on AC, user-active).
- Sets the screen saver idle time to 0 and remembers the previous value.
- `awake off` (or the timer expiring) restores the saved screen saver time.
- State lives in `~/.awake` (directory is user-only, mode 700).

## Install

```
mkdir -p ~/bin && cp awake ~/bin/awake && chmod +x ~/bin/awake
grep -q 'HOME/bin' ~/.zshrc 2>/dev/null || echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
```

## Security notes

- While `awake` is on, the screen saver (and any "require password after
  screen saver" lock that depends on it) will not start. Turn it off when you
  walk away from the machine.
- If the Mac reboots or the process is killed while on, `awake status` reports
  the leftover state, and `awake off` (or the next `awake on`) restores the
  original screen saver time instead of overwriting it.
- The timer argument must be a whole number, and values are passed to the
  background process as arguments rather than interpolated into a command
  string, so untrusted input cannot inject commands.
- The pid file is only trusted if it holds a number and that process is
  really `caffeinate`.
- The script changes a user-level preference (`com.apple.screensaver idleTime`)
  and restarts `cfprefsd` so the change takes effect. It does not need sudo and
  makes no network requests.

## License

MIT, see [LICENSE](LICENSE).
