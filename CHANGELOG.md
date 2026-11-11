# Changelog

## 1.9.0 (2026-11-11)

### Changed
- macOS: the menu bar icon comes back by itself. Any awake command opens SwiftBar if the icon is
  installed but SwiftBar isn't running (not for `menubar`, `uninstall` or internal commands, so
  "Hide icon until next login" still works). The agent LaunchAgent also opens SwiftBar at login.
  Re-run `awake agent on` once to pick up the new LaunchAgent. (PR #2)
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
