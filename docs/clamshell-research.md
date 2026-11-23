# Clamshell / virtual display research (macOS)

Status: notes only. Nothing here is implemented. Lid-closed behavior is **not yet tested**.

## Observed (M1 Pro MacBookPro18,1, macOS 26.7.3, lid open)
- vdisplay online (id 4) with the LG behind a KVM: `AppleClamshellCausesSleep = Yes`.
- Later, on battery with the LG apparently back: `AppleClamshellCausesSleep = No`.
- Suggests a real monitor flips the flag; the virtual display alone did not. Unconfirmed
  until tested with only the vdisplay attached.

## Lid-closed results (2026-11-23)
- Real monitor (LG via dock) + AC, lid closed ~30s: stayed awake. No Sleep/Wake in `pmset -g log`.
- vdisplay only, battery 28%, lid closed ~3m: slept. Log: `Entering Sleep state due to 'Clamshell Sleep'`
  at 00:38:38, woke at 00:41:52 on lid open. All caffeinate assertions were held and did not help.
- vdisplay only, AC: NOT yet tested (do this next).
- Note: `AppleClamshellCausesSleep` read "No" on battery with the dock detached, yet the Mac still slept.
  So that flag is not reliable for predicting lid-close sleep with only a virtual display.

## Pending hardware tests
1. Charger plugged in directly (no dock/LG), only vdisplay attached: run `awake clamshell`.
2. Close the lid ~60s on AC; read `pmset -g log` for 'Clamshell Sleep' (and try Screen Sharing).
3. Try `displayplacer "id:<id> enabled:false"` on a spare monitor.

## Idea: `awake display only` / `awake display restore`
Turn off physical monitors so only the vdisplay remains.
- displayplacer `enabled:false` (optional add-on; re-enable may need replug; screen ids can shift).
- BetterDisplay disconnect (separate app; CLI reliability with virtual displays unverified).
- Private `CGSConfigureDisplayEnabled` (unsupported; can break on macOS updates).
Safety: save layout first, never disable the last active display, auto-restore after a timeout.
Caveat: if macOS doesn't count the vdisplay for clamshell, this alone won't keep the Mac awake
with the lid closed; `pmset disablesleep 1` would still be needed.

## Display on/off tooling research (2026-11-23)

| Option | License | Activity | Notes |
|---|---|---|---|
| displayplacer (jakehilborn) | MIT (verified via GitHub API) | latest release v1.4.0 (2023-06), last push 2024-06 | `enabled:false` / `enabled:true`; Homebrew bottles exist for Sequoia and Tahoe |
| BetterDisplay + betterdisplaycli | no license on the repo (not open source); pricing of the CLI unconfirmed | very active | needs the app running; disconnect is Apple Silicon only; CLI reconnect of virtual displays reported unreliable |
| blackoutd | GPL-3.0 | active | built-in display only, private `CGSConfigureDisplayEnabled` |

Known risks: screen IDs can shift when displays wake in a different order (displayplacer README);
after `enabled:false` a screen may need unplugging/replugging to return. No report found of
`enabled:false` failing on Sequoia/Tahoe, and no confirmation it works there either: test on hardware.

Sources: displayplacer README (raw.githubusercontent.com/jakehilborn/displayplacer/master/README.md),
formulae.brew.sh/formula/displayplacer, BetterDisplay CLI wiki
(github.com/waydabber/BetterDisplay/wiki/Integration-features,-CLI), BetterDisplay discussion #3947.

## Proposed design (not implemented)
Optional add-on, like vdisplay: installed after asking, nothing runs unless the user opts in.
- `awake display only`: save the layout, disable physical monitors, leave the vdisplay.
- `awake display restore`: put the saved layout back.
- Look displays up by name/type at run time, never by a stored screen id.
- Never disable the last active display. Auto-restore after a timeout (default a few minutes unless
  confirmed), so a bad state can't leave the Mac with no screen.
- Tests with a fake displayplacer; then a manual hardware test (spare monitor first).

Gate: only worth building if macOS counts the vdisplay for clamshell mode. Battery test says it
did not; the AC test (vdisplay only, charger direct) decides. If it never counts, this is a layout
feature and `pmset disablesleep 1` stays the way to keep the Mac awake with the lid closed.

## Hardware test plan for displayplacer (when at the Mac)
1. `brew install jakehilborn/jakehilborn/displayplacer`; `displayplacer list` and note ids.
2. With a spare monitor: `displayplacer "id:<id> enabled:false"`, then `enabled:true`. Does it return
   without a replug? Do ids change after sleep/wake or a KVM switch?
3. Repeat with the LG behind the KVM, since ids may differ per input.
4. Re-run the lid-closed test on AC with only the vdisplay active.
