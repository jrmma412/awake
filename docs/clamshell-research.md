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
