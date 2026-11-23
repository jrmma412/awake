# Clamshell / virtual display research (macOS)

Status: notes only. Nothing here is implemented. Lid-closed behavior is **not yet tested**.

## Observed (M1 Pro MacBookPro18,1, macOS 26.7.3, lid open)
- vdisplay online (id 4) with the LG behind a KVM: `AppleClamshellCausesSleep = Yes`.
- Later, on battery with the LG apparently back: `AppleClamshellCausesSleep = No`.
- Suggests a real monitor flips the flag; the virtual display alone did not. Unconfirmed
  until tested with only the vdisplay attached.

## Pending hardware tests
1. Only vdisplay attached (KVM away), on AC: run `awake clamshell`.
2. Close the lid ~20s on AC; check reachability (Screen Sharing / SSH).
3. Try `displayplacer "id:<id> enabled:false"` on a spare monitor.

## Idea: `awake display only` / `awake display restore`
Turn off physical monitors so only the vdisplay remains.
- displayplacer `enabled:false` (optional add-on; re-enable may need replug; screen ids can shift).
- BetterDisplay disconnect (separate app; CLI reliability with virtual displays unverified).
- Private `CGSConfigureDisplayEnabled` (unsupported; can break on macOS updates).
Safety: save layout first, never disable the last active display, auto-restore after a timeout.
Caveat: if macOS doesn't count the vdisplay for clamshell, this alone won't keep the Mac awake
with the lid closed; `pmset disablesleep 1` would still be needed.
