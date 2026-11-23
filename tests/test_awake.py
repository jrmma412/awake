"""Checks that run without a desktop: syntax, versions, time parsing, safe commands, install/uninstall.
Linux tests run on Linux, macOS tests on macOS (CI runs both)."""
import ast
import os
import pwd
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
LINUX = REPO / "linux" / "awake"
MAC = REPO / "awake"
linux_only = pytest.mark.skipif(sys.platform != "linux", reason="Linux version")
mac_only = pytest.mark.skipif(sys.platform != "darwin", reason="macOS version")


def run(cmd, home, **kw):
    # AWAKE_*: never read the real /etc or /sys (a lid setting or a loaded vkms driver would change the output).
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
               AWAKE_LID_CONF=str(home / "awake-lid.conf"),
               AWAKE_VD_BOOT=str(home / "modules-load.d" / "awake-vdisplay.conf"),
               AWAKE_VKMS=str(home / "sys-module-vkms"), AWAKE_DRM=str(home / "sys-class-drm"),
               AWAKE_MODULES=str(home / "lib-modules"))
    env.update(kw.pop("env", {}))
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, env=env, timeout=60, **kw)


def script_version(path):
    return re.search(r"^VERSION=(\S+)", path.read_text(), re.M).group(1)


def pinned_ref(path):
    return re.search(r"^\s*local REF=(\S+)", path.read_text(), re.M).group(1)


def linux_funcs(home, body):
    """Run `body` in bash with the Linux script's time functions loaded."""
    text = LINUX.read_text()
    funcs = text[text.index("now() {"):text.index("# The keep-awake, jiggle and agent parts")]
    return run(["bash", "-c", funcs + "\n" + body], home)


def helper_source():
    text = LINUX.read_text()
    start = text.index("cat <<'PY'\n", text.index("helper_py() {")) + len("cat <<'PY'\n")
    return text[start:text.index("\nPY\n", start)]


# ---- both platforms ----
def test_formula_pins_a_release():
    formula = (REPO / "Formula" / "awake.rb").read_text()
    assert re.search(r'tag:\s+"v\d+\.\d+\.\d+"', formula)
    assert re.search(r'revision:\s+"[0-9a-f]{40}"', formula)


def test_installers_pin_the_script_version():
    assert pinned_ref(REPO / "install.sh") == "v" + script_version(MAC)
    assert pinned_ref(REPO / "linux" / "install.sh") == "v" + script_version(LINUX)


def test_both_versions_match():
    assert script_version(MAC) == script_version(LINUX)


# ---- Linux ----
@linux_only
@pytest.mark.parametrize("path", ["linux/awake", "linux/install.sh"])
def test_linux_syntax(path, tmp_path):
    assert run(["bash", "-n", REPO / path], tmp_path).returncode == 0


@linux_only
def test_linux_helper_is_valid_python():
    ast.parse(helper_source())


@linux_only
def test_linux_version_and_help(tmp_path):
    r = run([LINUX, "--version"], tmp_path)
    assert r.stdout.strip() == f"awake {script_version(LINUX)} (Linux)"
    r = run([LINUX, "help"], tmp_path)
    assert r.returncode == 0 and "awake jiggle" in r.stdout and "awake agent" in r.stdout


@linux_only
def test_linux_status_off_and_unknown_command(tmp_path):
    r = run([LINUX, "status"], tmp_path)
    assert r.stdout.strip() == "OFF" and r.returncode == 0   # 0 also when jiggle is off
    r = run([LINUX, "2x"], tmp_path)
    assert r.returncode == 1 and "unknown command or time" in r.stdout
    r = run([LINUX, "until", "5"], tmp_path)
    assert r.returncode == 1 and "bad time" in r.stdout
    assert not (tmp_path / ".awake" / "pid").exists()


@linux_only
@pytest.mark.parametrize("text,secs", [
    ("90", 90), ("45s", 45), ("30m", 1800), ("2h", 7200), ("1h30m", 5400), ("08", 8),
    ("0", None), ("abc", None), ("2x", None), ("1h30", None), ("9999999999", None), ("366d", None), ("", None),
])
def test_linux_parse_dur(text, secs, tmp_path):
    r = linux_funcs(tmp_path, f'parse_dur "{text}"')
    if secs is None:
        assert r.returncode != 0 and r.stdout == ""
    else:
        assert r.returncode == 0 and int(r.stdout) == secs


@linux_only
@pytest.mark.parametrize("text,ok", [
    ("5pm", True), ("5:30 pm", True), ("17:30", True), ("17", True), ("0:00", True), ("12am", True), ("12PM", True),
    ("5", False), ("13pm", False), ("24:00", False), ("9:5", False), ("5:60pm", False), ("noon", False),
])
def test_linux_parse_until(text, ok, tmp_path):
    r = linux_funcs(tmp_path, f'parse_until "{text}" && echo $REPLY')
    if ok:
        assert r.returncode == 0 and 0 < int(r.stdout) <= 86400 + 3600
    else:
        assert r.returncode != 0


@linux_only
def test_linux_until_times_agree(tmp_path):
    r = linux_funcs(tmp_path, 'parse_until 5:30pm; a=$REPLY; parse_until 17:30; echo $(( a - REPLY ))')
    assert abs(int(r.stdout)) <= 1


@linux_only
def test_linux_glide_stays_nearby_and_never_clicks():
    ns = {}
    exec(helper_source().split("\ncmd, a = sys.argv[1]")[0], ns)

    class FakeMouse:
        def __init__(self): self.moves = []
        def move(self, dx, dy): self.moves.append((dx, dy))

    for _ in range(20):
        m = FakeMouse()
        ns["glide"](m)
        x, y = sum(d[0] for d in m.moves), sum(d[1] for d in m.moves)
        assert 30 <= (x * x + y * y) ** 0.5 <= 260
        assert max(max(abs(a), abs(b)) for a, b in m.moves) <= 60


@linux_only
def test_linux_agent_cosmic_saves_and_restores(tmp_path):
    conf = tmp_path / ".config" / "cosmic" / "com.system76.CosmicIdle" / "v1"
    conf.mkdir(parents=True)
    setting = conf / "suspend_on_ac_time"
    saved = tmp_path / ".awake" / "agent.saved"
    saved.parent.mkdir()
    # A saved value selects the COSMIC method even where COSMIC is not running (CI).
    setting.write_text("Some(7200000)")
    saved.write_text("Some(7200000)")
    r = run([LINUX, "agent"], tmp_path)
    assert r.returncode == 0 and "agent mode: ON" in r.stdout
    assert setting.read_text() == "None" and saved.read_text() == "Some(7200000)"
    assert "agent mode: ON" in run([LINUX, "status"], tmp_path).stdout
    r = run([LINUX, "agent", "off"], tmp_path)
    assert r.returncode == 0 and setting.read_text() == "Some(7200000)" and not saved.exists()


@linux_only
def test_linux_agent_keeps_a_setting_changed_meanwhile(tmp_path):
    conf = tmp_path / ".config" / "cosmic" / "com.system76.CosmicIdle" / "v1"
    conf.mkdir(parents=True)
    setting = conf / "suspend_on_ac_time"
    saved = tmp_path / ".awake" / "agent.saved"
    saved.parent.mkdir()
    saved.write_text("unset")
    setting.write_text("Some(600000)")   # changed in Settings after agent mode was turned on
    assert "changed since" in run([LINUX, "agent", "status"], tmp_path).stdout
    run([LINUX, "agent", "off"], tmp_path)
    assert setting.read_text() == "Some(600000)" and not saved.exists()


@linux_only
def test_linux_agent_restores_system_default(tmp_path):
    conf = tmp_path / ".config" / "cosmic" / "com.system76.CosmicIdle" / "v1"
    conf.mkdir(parents=True)
    setting = conf / "suspend_on_ac_time"
    saved = tmp_path / ".awake" / "agent.saved"
    saved.parent.mkdir()
    saved.write_text("unset")
    setting.write_text("None")
    run([LINUX, "agent", "off"], tmp_path)
    assert not setting.exists() and not saved.exists()


@linux_only
def test_linux_install_and_uninstall(tmp_path):
    bashrc = tmp_path / ".bashrc"
    bashrc.write_text("export FOO=1")
    path = "/usr/bin:/bin"
    installer = REPO / "linux" / "install.sh"
    for _ in range(2):   # a second install must not stack PATH lines
        r = run([installer, "-y"], tmp_path, env={"PATH": path, "SHELL": "/bin/bash"})
        assert r.returncode == 0, r.stdout + r.stderr
    installed = tmp_path / ".local" / "bin" / "awake"
    assert installed.read_text() == LINUX.read_text() and os.access(installed, os.X_OK)
    assert bashrc.read_text().count("# added by awake") == 1
    (tmp_path / "awake-lid.conf").write_text("[Login]\n")   # a lid setting from 'awake clamshell' stays
    vd_boot = tmp_path / "modules-load.d" / "awake-vdisplay.conf"   # and so does the virtual display setting
    vd_boot.parent.mkdir()
    vd_boot.write_text("vkms\n")
    r = run([installed, "uninstall", "-y"], tmp_path, env={"PATH": path})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "keep your lid setting" in r.stdout and (tmp_path / "awake-lid.conf").exists()
    assert "keep the virtual display setting" in r.stdout and vd_boot.exists()
    assert not installed.exists() and not (tmp_path / ".awake").exists()
    assert bashrc.read_text().strip() == "export FOO=1"


# ---- macOS ----
@mac_only
@pytest.mark.parametrize("path", ["awake", "install.sh"])
def test_mac_syntax(path, tmp_path):
    assert run(["zsh", "-n", REPO / path], tmp_path).returncode == 0


@mac_only
def test_mac_version_and_help(tmp_path):
    assert run([MAC, "--version"], tmp_path).stdout.strip() == f"awake {script_version(MAC)}"
    r = run([MAC, "help"], tmp_path)
    assert r.returncode == 0 and "awake jiggle" in r.stdout


@mac_only
def test_mac_rejects_bad_times(tmp_path):
    r = run([MAC, "2x"], tmp_path)
    assert r.returncode == 1 and "unknown command or time" in r.stdout
    r = run([MAC, "until", "5"], tmp_path)
    assert r.returncode == 1 and "bad time" in r.stdout
    assert not (tmp_path / ".awake" / "pid").exists()


@mac_only
def test_mac_clamshell_only_reads(tmp_path):
    """awake clamshell prints the state and never runs sudo or changes power settings."""
    fake = tmp_path / "fakebin"
    fake.mkdir()
    calls = tmp_path / "calls.log"
    (fake / "sudo").write_text(f'#!/bin/sh\necho "sudo $*" >> "{calls}"\nexit 1\n')
    (fake / "pmset").write_text(f'#!/bin/sh\necho "pmset $*" >> "{calls}"\nexec /usr/bin/pmset "$@"\n')
    for f in fake.iterdir():
        f.chmod(0o755)
    r = run([MAC, "clamshell"], tmp_path, env={"PATH": f"{fake}:{os.environ['PATH']}"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "closing the lid sleeps the Mac:" in r.stdout
    assert "sleep disabled (pmset):" in r.stdout
    logged = calls.read_text().splitlines() if calls.exists() else []
    assert not [c for c in logged if c.startswith("sudo")]
    assert all(c.split()[1] == "-g" for c in logged if c.startswith("pmset"))


@mac_only
def test_mac_clamshell_bad_argument(tmp_path):
    r = run([MAC, "clamshell", "on"], tmp_path)
    assert r.returncode == 1 and "usage: awake clamshell" in r.stdout


LID_FILE = "[Login]\nHandleLidSwitchExternalPower=lock\nHandleLidSwitchDocked=ignore\n"


def fake_logind(tmp_path, lid=True, closed=False, ac=True, docked=False, bat="suspend", ext="", dock="ignore",
                logind=True, lock=None):
    """A stand-in busctl (logind + UPower answers) and a sudo that only logs, both first on PATH.
    lock: (what, who, why, uid, pid) of one more inhibitor lock. logind=False: logind doesn't answer."""
    fake = tmp_path / "fakebin"
    fake.mkdir(exist_ok=True)
    calls = tmp_path / "calls.log"
    b = lambda v: "true" if v else "false"
    locks = '["sleep","UPower","x","delay",0,1]'
    if lock:
        what, who, why, uid, pid = lock
        locks += f',["{what}","{who}","{why}","block",{uid},{pid}]'
    say = (lambda line: line) if logind else (lambda line: "exit 1")
    q = '"'   # built outside the f-string below: Python < 3.12 allows no backslash inside {...}
    s_bat, s_ext, s_dock = (say(f"echo 's {q}{v}{q}'") for v in (bat, ext, dock))
    (fake / "busctl").write_text(f"""#!/bin/sh
case "$*" in
  *ListInhibitors*) echo '{{"type":"a(ssssuu)","data":[[{locks}]]}}';;
  *LidIsPresent) echo "b {b(lid)}";;
  *LidClosed) {say(f'echo "b {b(closed)}"')};;
  *OnExternalPower) {say(f'echo "b {b(ac)}"')};;
  *" Docked") {say(f'echo "b {b(docked)}"')};;
  *HandleLidSwitch) {s_bat};;
  *HandleLidSwitchExternalPower) {s_ext};;
  *HandleLidSwitchDocked) {s_dock};;
  *) exit 1;;
esac
""")
    (fake / "sudo").write_text(f'#!/bin/sh\necho "sudo $*" >> "{calls}"\nexit 1\n')
    for f in fake.iterdir():
        f.chmod(0o755)
    return {"PATH": f"{fake}:{os.environ['PATH']}"}, calls


def printed_commands(out):
    """The indented command lines awake prints for you to run."""
    return [ln.strip() for ln in out.splitlines() if re.match(r"  (sudo|printf) ", ln)]


@linux_only
def test_linux_clamshell_no_lid(tmp_path):
    env, calls = fake_logind(tmp_path, lid=False)
    r = run([LINUX, "clamshell"], tmp_path, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "lid:" in r.stdout and "doesn't report a lid" in r.stdout and "sudo" not in r.stdout
    assert not calls.exists()


@linux_only
def test_linux_clamshell_prints_working_commands_and_never_runs_sudo(tmp_path):
    env, calls = fake_logind(tmp_path)
    r = run([LINUX, "clamshell"], tmp_path, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "closing the lid right now:" in r.stdout and "suspend (plugged in)" in r.stdout
    assert "Closing the lid while plugged in does: suspend." in r.stdout
    cmds = printed_commands(r.stdout)
    assert cmds[-2] == "sudo systemctl reload systemd-logind"
    # Pasted as one block, every printed line must be valid shell (no stray notes on a command line) ...
    assert subprocess.run(["bash", "-n"], input="\n".join(cmds), text=True).returncode == 0
    # ... and the printf must write exactly the drop-in we mean.
    printf = next(c for c in cmds if c.startswith("printf "))
    assert printf.endswith("| sudo tee " + str(tmp_path / "awake-lid.conf"))
    out = subprocess.run(["bash", "-c", printf.split(" | ")[0]], capture_output=True, text=True).stdout
    assert out == LID_FILE
    assert not calls.exists()   # printed for you to run, never run
    assert not (tmp_path / "awake-lid.conf").exists()


@linux_only
@pytest.mark.parametrize("bat,ext,expect", [("suspend", "lock", "won't suspend this PC while it's plugged in"),
                                            ("ignore", "", "plugged in or on battery")])
def test_linux_clamshell_lid_already_kept_running(tmp_path, bat, ext, expect):
    env, _ = fake_logind(tmp_path, bat=bat, ext=ext)
    r = run([LINUX, "clamshell"], tmp_path, env=env)
    assert expect in r.stdout and "To undo" not in r.stdout and "sudo" not in r.stdout
    (tmp_path / "awake-lid.conf").write_text(LID_FILE)   # awake's own setting: offer the undo
    out = run([LINUX, "clamshell"], tmp_path, env=env).stdout
    assert printed_commands(out) == ["sudo rm " + str(tmp_path / "awake-lid.conf") + " && sudo systemctl reload systemd-logind"]


@linux_only
def test_linux_clamshell_file_not_in_effect(tmp_path):
    env, _ = fake_logind(tmp_path)   # logind still says suspend
    (tmp_path / "awake-lid.conf").write_text(LID_FILE)
    r = run([LINUX, "clamshell"], tmp_path, env=env)
    assert "exists but isn't in effect" in r.stdout and "sudo tee" not in r.stdout
    assert "sudo systemctl reload systemd-logind" in printed_commands(r.stdout)


@linux_only
def test_linux_clamshell_on_battery_lid_closed(tmp_path):
    env, _ = fake_logind(tmp_path, ac=False, closed=True)
    r = run([LINUX, "clamshell"], tmp_path, env=env)
    assert re.search(r"power:\s+battery\n", r.stdout) and re.search(r"lid:\s+closed\n", r.stdout)
    assert re.search(r"right now:\s+suspend \(on battery\)", r.stdout)


@linux_only
def test_linux_clamshell_docked(tmp_path):
    env, _ = fake_logind(tmp_path, ac=False, docked=True)
    r = run([LINUX, "clamshell"], tmp_path, env=env)
    assert "ignore (2+ displays or docked)" in r.stdout
    env, _ = fake_logind(tmp_path, ext="lock", dock="suspend")
    r = run([LINUX, "clamshell"], tmp_path, env=env)
    assert "with 2+ displays or docked does: suspend" in r.stdout and "while plugged in does" not in r.stdout


@linux_only
def test_linux_clamshell_logind_silent(tmp_path):
    env, _ = fake_logind(tmp_path, logind=False)
    r = run([LINUX, "clamshell"], tmp_path, env=env)
    assert r.returncode == 0 and "Couldn't read the lid settings" in r.stdout and "sudo" not in r.stdout


@linux_only
def test_linux_clamshell_gnome_took_the_lid(tmp_path):
    """GNOME's lock says your user name as "who": awake names the program from its process instead."""
    gsd = tmp_path / "gsd-power"
    gsd.symlink_to(shutil.which("sleep"))
    proc = subprocess.Popen([str(gsd), "30"])
    try:
        user = pwd.getpwuid(os.getuid()).pw_name
        env, _ = fake_logind(tmp_path, lock=("handle-lid-switch", user,
                                             "External monitor attached or configuration changed recently",
                                             os.getuid(), proc.pid))
        r = run([LINUX, "clamshell"], tmp_path, env=env)
    finally:
        proc.kill()
        proc.wait()
    assert "lid handled by:" in r.stdout and "gsd-power (External monitor attached" in r.stdout
    assert "gsd-power is handling the lid" in r.stdout and f"{user} is handling" not in r.stdout
    assert "sudo tee" not in r.stdout


@linux_only
def test_linux_clamshell_kde_took_the_lid(tmp_path):
    """A real program name in "who" is kept as is (/proc/PID/comm would cut it to 15 characters)."""
    proc = subprocess.Popen([shutil.which("sleep"), "30"])
    try:
        env, _ = fake_logind(tmp_path, lock=("handle-power-key:handle-lid-switch", "org_kde_powerdevil",
                                             "KDE handles power events", os.getuid(), proc.pid))
        r = run([LINUX, "clamshell"], tmp_path, env=env)
    finally:
        proc.kill()
        proc.wait()
    assert "org_kde_powerdevil is handling the lid" in r.stdout and "sudo tee" not in r.stdout


@linux_only
def test_linux_clamshell_counts_another_users_lid_lock(tmp_path):
    # logind obeys a lock from a process outside any login session (e.g. a user service), whoever owns
    # it; it only skips locks from inactive sessions. (No such process here: it counts.)
    env, _ = fake_logind(tmp_path, lock=("handle-lid-switch", "PowerDevil", "x", os.getuid() + 1, 2 ** 31 - 1))
    r = run([LINUX, "clamshell"], tmp_path, env=env)
    assert "PowerDevil is handling the lid" in r.stdout and "sudo tee" not in r.stdout


@linux_only
def test_linux_clamshell_unknown_power_source(tmp_path):
    env, _ = fake_logind(tmp_path, ext="lock")
    fake = Path(env["PATH"].split(":")[0]) / "busctl"
    fake.write_text(fake.read_text().replace('*OnExternalPower) echo "b true";;', "*OnExternalPower) exit 1;;"))
    r = run([LINUX, "clamshell"], tmp_path, env=env)
    assert re.search(r"power:\s+unknown\n", r.stdout)
    assert "lock if plugged in, suspend on battery (power source unknown)" in r.stdout


@linux_only
def test_linux_clamshell_bad_argument(tmp_path):
    r = run([LINUX, "clamshell", "on"], tmp_path)
    assert r.returncode == 1 and "usage: awake clamshell" in r.stdout


@linux_only
def test_linux_status_reminds_about_the_lid_setting(tmp_path):
    env, _ = fake_logind(tmp_path, ext="lock")
    assert "clamshell:" not in run([LINUX, "status"], tmp_path, env=env).stdout
    (tmp_path / "awake-lid.conf").write_text(LID_FILE)
    r = run([LINUX, "status"], tmp_path, env=env)
    assert r.returncode == 0 and "clamshell: closing the lid won't suspend" in r.stdout
    env, _ = fake_logind(tmp_path)   # file there, but logind still suspends
    r = run([LINUX, "status"], tmp_path, env=env)
    assert r.returncode == 0 and "isn't in effect (plugged in, the lid still does: suspend)" in r.stdout


@linux_only
def test_linux_all_off_without_agent(tmp_path):
    r = run([LINUX, "all", "off"], tmp_path)
    assert r.returncode == 0
    assert "nothing to stop (it was never installed" in r.stdout
    assert r.stdout.strip().endswith("awake all: everything is off")


@linux_only
def test_linux_all_off_says_so_when_busy(tmp_path):
    (tmp_path / ".awake" / "lock").mkdir(parents=True)   # another awake command holds the lock
    r = run([LINUX, "all", "off"], tmp_path)
    assert r.returncode == 1 and "busy" in r.stdout
    assert "everything is off" not in r.stdout and "not everything could be turned off" in r.stdout


@linux_only
@pytest.mark.parametrize("args", [["jiggle", "bogus"], ["jiggle", "random", "bogus"], ["all", "random", "bogus"]])
def test_linux_bad_jiggle_arguments_print_usage(tmp_path, args):
    r = run([LINUX] + args, tmp_path)
    assert r.returncode == 1 and "usage: awake" in r.stdout and "[simple|random]" in r.stdout
    assert not (tmp_path / ".awake" / "jiggle.pid").exists()


def fake_vdisplay(tmp_path, status_rc=0):
    """A stand-in vdisplay on PATH: logs its calls, and `status` answers with status_rc."""
    fake = tmp_path / "fakebin"
    fake.mkdir(exist_ok=True)
    calls = tmp_path / "vd-calls.log"
    (fake / "vdisplay").write_text(f"""#!/bin/sh
echo "vdisplay $*" >> "{calls}"
if [ "$1" = status ]; then
  [ {status_rc} -eq 1 ] && {{ echo "vdisplay: not running"; exit 1; }}
  echo "vdisplay: running (pid 4242)"
  echo '  display id 17, 1920x1080 @ 60Hz, name "vdisplay"'
  exit {status_rc}
fi
exit 0
""")
    (fake / "vdisplay").chmod(0o755)
    return {"PATH": f"{fake}:{os.environ['PATH']}"}, calls


@mac_only
def test_mac_display_not_installed(tmp_path):
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}   # no Homebrew, no vdisplay
    if Path("/opt/homebrew/bin/vdisplay").exists():
        pytest.skip("vdisplay is really installed on this Mac")
    r = run([MAC, "display", "status"], tmp_path, env=env)
    assert r.returncode == 0 and "display: not installed" in r.stdout
    # Not in a terminal: installs nothing. (awake finds Homebrew in /opt/homebrew even when PATH
    # lacks it, so on a Mac with Homebrew it asks to be run in Terminal; without, it says so.)
    r = run([MAC, "display"], tmp_path, env=env)
    assert r.returncode == 1
    assert "needs installing" in r.stdout or "installed with Homebrew" in r.stdout
    assert "installing vdisplay" not in r.stdout
    # awake status stays quiet about the add-on when it isn't installed.
    assert "display:" not in run([MAC, "status"], tmp_path, env=env).stdout


@mac_only
@pytest.mark.parametrize("rc,expect", [(0, "display: ON (virtual display id 17, 1920x1080 @ 60Hz"),
                                       (1, "display: OFF"),
                                       (2, "hasn't brought the virtual display online")])
def test_mac_display_status_reads_vdisplay(tmp_path, rc, expect):
    env, calls = fake_vdisplay(tmp_path, rc)
    r = run([MAC, "display", "status"], tmp_path, env=env)
    assert expect in r.stdout
    assert r.returncode == (1 if rc == 2 else 0)
    assert expect in run([MAC, "status"], tmp_path, env=env).stdout
    assert "virtual display (awake display):" in run([MAC, "clamshell"], tmp_path, env=env).stdout


@mac_only
def test_mac_display_menu_items(tmp_path):
    env, _ = fake_vdisplay(tmp_path, 0)
    out = run([MAC, "_menu"], tmp_path, env=env).stdout
    assert "Virtual display: ON" in out and "param1=display param2=off" in out
    env, _ = fake_vdisplay(tmp_path, 1)   # same fake, now reporting "not running"
    out = run([MAC, "_menu"], tmp_path, env=env).stdout
    assert "param1=display param2=on" in out


@mac_only
def test_mac_display_off_stops_vdisplay(tmp_path):
    env, calls = fake_vdisplay(tmp_path, 0)
    r = run([MAC, "display", "off"], tmp_path, env=env)
    assert r.returncode == 0 and "display OFF" in r.stdout
    assert "vdisplay stop" in calls.read_text()


@mac_only
def test_mac_display_bad_argument(tmp_path):
    r = run([MAC, "display", "bogus"], tmp_path)
    assert r.returncode == 1 and "usage: awake display" in r.stdout


@mac_only
@pytest.mark.parametrize("plist", ["sh.brew.vdisplay.plist", "homebrew.mxcl.vdisplay.plist"])
def test_mac_display_sees_login_item(tmp_path, plist):
    env, _ = fake_vdisplay(tmp_path, 0)
    agents = tmp_path / "Library" / "LaunchAgents"
    agents.mkdir(parents=True)
    (agents / plist).write_text("<plist/>")
    assert "starts at login" in run([MAC, "display", "status"], tmp_path, env=env).stdout


# ---- Linux virtual display (awake display) ----
FAKE_RANDR = r"""#!/bin/sh
echo "cosmic-randr $* WAYLAND_DISPLAY=$WAYLAND_DISPLAY" >> "@CALLS@"
@ANSWER@
read en w h < "@STATE@"
case "$1" in
  list)
    echo 'output "DP-3" enabled=#true {'
    echo '  modes {'
    echo '    mode 2560 1440 164958 current=#true preferred=#true'
    echo '    mode 1920 1080 60000'
    echo '  }'
    echo '}'
    echo "output \"Virtual-1\" enabled=#$en {"
    echo '  position 2560 0'
    echo '  modes {'
    cur=""
    for m in "4096 2160 60000" "2560 1600 59987" "2560 1600 59972" "1920 1080 60000" "1280 720 60000" "1024 768 60004"; do
      set -- $m; extra=""
      if [ "$en" = true ] && [ -z "$cur" ] && [ "$1" = "$w" ] && [ "$2" = "$h" ]; then extra=" current=#true"; cur=1; fi
      [ "$1" = 1024 ] && extra="$extra preferred=#true"
      echo "    mode $1 $2 $3$extra"
    done
    echo '  }'
    echo '}';;
  mode) echo "true $5 $6" > "@STATE@";;         # mode --refresh HZ NAME W H (like COSMIC, it also turns it on)
  enable) echo "true $w $h" > "@STATE@";;
  disable) echo "false $w $h" > "@STATE@";;
esac
"""


_VKMS_LOGS = []   # every fake_vkms() log, checked after each test


@pytest.fixture(autouse=True)
def _display_never_runs_sudo_or_switches_the_display(tmp_path):
    """For every display test: awake never ran sudo, and never switched the virtual display on or off
    (cosmic-randr enable/disable once froze COSMIC). It asks for tmp_path so it runs before pytest
    may delete that folder."""
    yield
    while _VKMS_LOGS:
        for ln in randr_calls(_VKMS_LOGS.pop()):
            assert not re.match(r"sudo |cosmic-randr (enable|disable)\b", ln), ln


def fake_vkms(tmp_path, loaded=True, connected=True, boot=False, enabled=True, mode=(1024, 768), answer=True,
              desktop="COSMIC", cosmic_running=True, has_driver=True, kernel_updated=False, vm_screen=False,
              sysfs_on=True):
    """A stand-in kernel (the sysfs bits awake reads), a modules-load.d folder, and a cosmic-randr
    that keeps the virtual display's state in a file. Paths match the AWAKE_* defaults in run().
    vm_screen adds a VM's own screen as Virtual-1, so vkms's is Virtual-2 (the kernel numbers
    connectors of a type across all cards). kernel_updated: this kernel's module folder is gone."""
    drm = tmp_path / "sys-class-drm"
    devices = tmp_path / "sys-devices"
    (devices / "faux" / "vkms").mkdir(parents=True)
    (devices / "pci0").mkdir()
    (devices / "pci1").mkdir()
    vk, gpu, virt = ("card1", "card2", "Virtual-2") if vm_screen else ("card0", "card1", "Virtual-1")
    cards = [(vk, devices / "faux" / "vkms"), (gpu, devices / "pci0")]
    conns = [(vk + "-" + virt, "connected" if connected else "disconnected", sysfs_on),
             (vk + "-Writeback-1", "unknown", False), (gpu + "-DP-3", "connected", True)]
    if vm_screen:   # listed first, so awake has to check which driver each screen belongs to
        cards.append(("card0", devices / "pci1"))
        conns.append(("card0-Virtual-1", "connected", True))
    for card, dev in cards:
        (drm / card).mkdir(parents=True)
        (drm / card / "device").symlink_to(dev)
    for conn, status, on in conns:
        (drm / conn).mkdir()
        (drm / conn / "status").write_text(status + "\n")
        (drm / conn / "enabled").write_text("enabled\n" if on else "disabled\n")
    if loaded:
        (tmp_path / "sys-module-vkms").mkdir()
    if not kernel_updated:
        (tmp_path / "lib-modules" / os.uname().release).mkdir(parents=True)
    boot_file = tmp_path / "modules-load.d" / "awake-vdisplay.conf"
    boot_file.parent.mkdir()
    if boot:
        boot_file.write_text("vkms\n")
    state = tmp_path / "randr.state"
    state.write_text("%s %d %d\n" % ("true" if enabled else "false", mode[0], mode[1]))
    calls = tmp_path / "calls.log"
    fake = tmp_path / "fakebin"
    fake.mkdir(exist_ok=True)
    randr = FAKE_RANDR.replace("@CALLS@", str(calls)).replace("@STATE@", str(state))
    (fake / "cosmic-randr").write_text(randr.replace("@ANSWER@", "" if answer else "exec sleep 30"))
    (fake / "sudo").write_text('#!/bin/sh\necho "sudo $*" >> "%s"\nexit 1\n' % calls)
    (fake / "pgrep").write_text('#!/bin/sh\ncase "$*" in *cosmic-comp*) exit %d;; esac\nexit 1\n'
                                % (0 if cosmic_running else 1))
    (fake / "modinfo").write_text('#!/bin/sh\n[ "$*" = "-n vkms" ] && [ %s = yes ] && echo /lib/modules/test/vkms.ko\n'
                                  % ("yes" if has_driver else "no"))
    for f in fake.iterdir():
        f.chmod(0o755)
    env = {"PATH": "%s:%s" % (fake, os.environ["PATH"]), "WAYLAND_DISPLAY": "wayland-test",
           "XDG_CURRENT_DESKTOP": desktop}
    _VKMS_LOGS.append(calls)
    return env, calls, state, boot_file


def randr_calls(calls):
    return [ln for ln in calls.read_text().splitlines()] if calls.exists() else []


@linux_only
def test_linux_display_not_set_up_prints_the_boot_command(tmp_path):
    env, calls, _, boot_file = fake_vkms(tmp_path, loaded=False)
    r = run([LINUX, "display"], tmp_path, env=env)
    assert r.returncode == 1, r.stdout + r.stderr
    cmds = [ln.strip() for ln in r.stdout.splitlines() if ln.startswith("  ")]
    assert cmds == ["echo vkms | sudo tee %s" % boot_file]
    assert subprocess.run(["bash", "-n"], input="\n".join(cmds), text=True).returncode == 0
    assert not calls.exists()   # neither sudo nor cosmic-randr ran
    assert run([LINUX, "display", "status"], tmp_path, env=env).stdout == "display: not set up (add it with 'awake display')\n"
    assert "display:" not in run([LINUX, "status"], tmp_path, env=env).stdout   # status stays quiet until it's set up


@linux_only
def test_linux_display_set_up_waits_for_the_restart(tmp_path):
    env, calls, _, _ = fake_vkms(tmp_path, loaded=False, boot=True)
    r = run([LINUX, "display"], tmp_path, env=env)
    assert r.returncode == 0 and "starts at the next restart" in r.stdout, r.stdout
    assert "display: set up; it starts at the next restart" in run([LINUX, "status"], tmp_path, env=env).stdout
    r = run([LINUX, "display", "2560x1600"], tmp_path, env=env)   # a size can't be set until then: say so
    assert r.returncode == 0 and "Run 'awake display 2560x1600' again after the restart" in r.stdout, r.stdout
    assert not calls.exists()


@linux_only
def test_linux_display_kernel_without_vkms(tmp_path):
    env, calls, _, boot_file = fake_vkms(tmp_path, loaded=False, has_driver=False)
    r = run([LINUX, "display"], tmp_path, env=env)
    assert r.returncode == 1 and "no vkms driver" in r.stdout and "sudo" not in r.stdout, r.stdout


@linux_only
def test_linux_display_kernel_updated_without_a_restart(tmp_path):
    # modinfo can't find vkms because this kernel's module folder is gone (a kernel update not yet
    # booted): that's no reason to hold back the setup command, which works after the restart.
    env, calls, _, boot_file = fake_vkms(tmp_path, loaded=False, has_driver=False, kernel_updated=True)
    r = run([LINUX, "display"], tmp_path, env=env)
    assert r.returncode == 1 and "  echo vkms | sudo tee %s" % boot_file in r.stdout.splitlines(), r.stdout


@linux_only
def test_linux_display_sets_1080p_and_never_switches_it(tmp_path):
    env, calls, state, _ = fake_vkms(tmp_path, boot=True)   # COSMIC put it at the driver's default 1024x768
    r = run([LINUX, "display"], tmp_path, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout == "display: ON (virtual display Virtual-1, 1920x1080 @ 60 Hz, also after restarts)\n"
    assert state.read_text().split() == ["true", "1920", "1080"]
    log = randr_calls(calls)
    assert "cosmic-randr mode --refresh 60.000 Virtual-1 1920 1080 WAYLAND_DISPLAY=wayland-test" in log
    assert not any(" enable " in ln or " disable " in ln or ln.startswith("sudo") for ln in log)
    assert "display: ON (virtual display Virtual-1, 1920x1080 @ 60 Hz" in run([LINUX, "status"], tmp_path, env=env).stdout


@linux_only
def test_linux_display_keeps_a_size_you_chose(tmp_path):
    env, calls, state, _ = fake_vkms(tmp_path, mode=(2560, 1600))
    env["LC_ALL"] = "de_DE.UTF-8"   # a decimal-comma locale (where installed) still prints 59.99
    r = run([LINUX, "display"], tmp_path, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "2560x1600 @ 59.99 Hz, until the next restart" in r.stdout
    assert r.stdout.splitlines()[-1] == "  echo vkms | sudo tee %s" % (tmp_path / "modules-load.d" / "awake-vdisplay.conf")
    assert not any(" mode " in ln for ln in randr_calls(calls))


@linux_only
@pytest.mark.parametrize("args", [["display", "2560x1600"], ["display", "on", "2560x1600"]])
def test_linux_display_sets_the_size_you_ask_for(tmp_path, args):
    env, calls, state, _ = fake_vkms(tmp_path, mode=(1920, 1080))
    r = run([LINUX] + args, tmp_path, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "cosmic-randr mode --refresh 59.987 Virtual-1 2560 1600 WAYLAND_DISPLAY=wayland-test" in randr_calls(calls)
    assert "2560x1600 @ 59.99 Hz" in r.stdout


@linux_only
def test_linux_display_rejects_a_size_it_does_not_offer(tmp_path):
    env, calls, state, _ = fake_vkms(tmp_path, mode=(1920, 1080))
    r = run([LINUX, "display", "1234x567"], tmp_path, env=env)
    assert r.returncode == 1
    assert "can't be 1234x567. Sizes it offers: 4096x2160 2560x1600 1920x1080 1280x720 1024x768" in r.stdout
    assert state.read_text().split() == ["true", "1920", "1080"]


@linux_only
def test_linux_display_turned_off_in_cosmic_is_left_to_you(tmp_path):
    env, calls, state, _ = fake_vkms(tmp_path, enabled=False, mode=(1920, 1080))
    r = run([LINUX, "display"], tmp_path, env=env)
    assert r.returncode == 1 and "turned off in COSMIC's display settings" in r.stdout, r.stdout
    assert state.read_text().split()[0] == "false"
    assert not any(" enable " in ln for ln in randr_calls(calls))
    assert "display: OFF (virtual display Virtual-1 is turned off" in run([LINUX, "display", "status"], tmp_path, env=env).stdout


@linux_only
def test_linux_display_size_for_a_display_turned_off_is_left_to_you(tmp_path):
    env, calls, state, _ = fake_vkms(tmp_path, enabled=False, mode=(1920, 1080))
    r = run([LINUX, "display", "2560x1600"], tmp_path, env=env)   # setting a mode would also turn it on
    assert r.returncode == 1 and "turned off in COSMIC's display settings" in r.stdout, r.stdout
    assert state.read_text().split() == ["false", "1920", "1080"]
    assert not any(" mode " in ln for ln in randr_calls(calls))


@linux_only
def test_linux_display_off_prints_the_removal_and_changes_nothing(tmp_path):
    env, calls, state, boot_file = fake_vkms(tmp_path, boot=True, mode=(1920, 1080))
    r = run([LINUX, "display", "off"], tmp_path, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "  sudo rm %s" % boot_file in r.stdout.splitlines()
    assert boot_file.exists() and state.read_text().split() == ["true", "1920", "1080"]
    assert not calls.exists()


@linux_only
def test_linux_display_off_names_other_files_that_load_vkms(tmp_path):
    env, calls, _, boot_file = fake_vkms(tmp_path)
    other = boot_file.parent / "my modules.conf"   # a space in the name: still one file
    other.write_text("lp\nvkms\n")
    r = run([LINUX, "display", "off"], tmp_path, env=env)
    out = r.stdout.splitlines()
    assert "vkms is loaded at boot by %s: remove its 'vkms' line (as root), then restart." % other in out, r.stdout
    assert "sudo rm" not in r.stdout and "Run this yourself" not in r.stdout, r.stdout
    boot_file.write_text("vkms\n")   # awake's own file too: its sudo rm, and the other one "also" loads it
    out = run([LINUX, "display", "off"], tmp_path, env=env).stdout.splitlines()
    assert out[1:3] == ["Run this yourself, then restart the PC:", "  sudo rm %s" % boot_file], out
    assert "vkms is also loaded at boot by %s: remove its 'vkms' line (as root), then restart." % other in out, out


@linux_only
def test_linux_display_off_before_the_restart(tmp_path):
    env, calls, _, boot_file = fake_vkms(tmp_path, loaded=False, boot=True)
    r = run([LINUX, "display", "off"], tmp_path, env=env)
    assert r.returncode == 0 and r.stdout.splitlines() == [
        "awake: the virtual display isn't there yet: it starts at the next restart, when the vkms driver loads.",
        "To cancel it, run this yourself:", "  sudo rm %s" % boot_file], r.stdout


@linux_only
def test_linux_display_off_when_not_set_up(tmp_path):
    env, calls, _, _ = fake_vkms(tmp_path, loaded=False)
    r = run([LINUX, "display", "off"], tmp_path, env=env)
    assert r.returncode == 0 and "nothing to turn off" in r.stdout


@linux_only
@pytest.mark.parametrize("how", ["no desktop", "GNOME", "SSH, COSMIC not running"])
def test_linux_display_on_another_desktop(tmp_path, how):
    kw = {"GNOME": dict(desktop="ubuntu:GNOME", cosmic_running=False),
          "SSH, COSMIC not running": dict(desktop="", cosmic_running=False)}
    env, calls, _, _ = fake_vkms(tmp_path, **kw.get(how, {}))
    if how == "no desktop":
        runtime = tmp_path / "runtime"   # no Wayland socket to talk to
        runtime.mkdir()
        env.update(WAYLAND_DISPLAY="", XDG_RUNTIME_DIR=str(runtime))
    r = run([LINUX, "display"], tmp_path, env=env)
    assert r.returncode == 0 and "isn't COSMIC" in r.stdout, r.stdout
    assert "display: ON (virtual display Virtual-1, until the next restart)" in r.stdout   # from sysfs
    assert not calls.exists()


@linux_only
def test_linux_display_cosmic_not_answering(tmp_path):
    env, calls, _, _ = fake_vkms(tmp_path, answer=False)
    r = run([LINUX, "display"], tmp_path, env=env)
    assert r.returncode == 1 and "COSMIC didn't answer" in r.stdout, r.stdout


@linux_only
def test_linux_display_finds_the_desktop_from_ssh(tmp_path):
    import socket
    env, calls, _, _ = fake_vkms(tmp_path, mode=(1920, 1080))
    runtime = tmp_path / "rt"
    runtime.mkdir()
    (runtime / "wayland-0.lock").write_text("")
    sock = socket.socket(socket.AF_UNIX)
    sock.bind(str(runtime / "wayland-1"))
    try:
        env.update(WAYLAND_DISPLAY="", XDG_RUNTIME_DIR=str(runtime), XDG_CURRENT_DESKTOP="")   # COSMIC found by its process
        r = run([LINUX, "display", "status"], tmp_path, env=env)
    finally:
        sock.close()
    assert "display: ON (virtual display Virtual-1, 1920x1080 @ 60 Hz" in r.stdout, r.stdout
    assert randr_calls(calls)[0].endswith("WAYLAND_DISPLAY=wayland-1")


@linux_only
@pytest.mark.parametrize("desktop, running", [("GNOME", True), ("COSMIC", False)])
def test_linux_display_either_sign_of_cosmic_counts(tmp_path, desktop, running):
    # XDG_CURRENT_DESKTOP set to something else on COSMIC (for app theming): its compositor still counts.
    # And XDG_CURRENT_DESKTOP=COSMIC is enough when its compositor isn't found (no pgrep, another name).
    env, calls, state, _ = fake_vkms(tmp_path, desktop=desktop, cosmic_running=running)
    r = run([LINUX, "display"], tmp_path, env=env)
    assert r.returncode == 0 and state.read_text().split() == ["true", "1920", "1080"], r.stdout


@linux_only
@pytest.mark.parametrize("on", [True, False])
def test_linux_display_picks_vkms_next_to_a_vm_screen(tmp_path, on):
    # In a VM, the VM's own screen is Virtual-1 and vkms's is Virtual-2: awake reports the vkms one.
    env, calls, _, _ = fake_vkms(tmp_path, vm_screen=True, sysfs_on=on, desktop="GNOME", cosmic_running=False)
    out = run([LINUX, "display", "status"], tmp_path, env=env).stdout
    assert out == ("display: ON (virtual display Virtual-2, until the next restart)\n" if on else
                   "display: OFF (virtual display Virtual-2 is connected but not in use; "
                   "turn it on in your display settings)\n"), out


@linux_only
def test_linux_display_driver_without_a_display(tmp_path):
    env, calls, _, _ = fake_vkms(tmp_path, connected=False)
    r = run([LINUX, "display"], tmp_path, env=env)
    assert r.returncode == 1 and "shows no virtual display" in r.stdout


@linux_only
@pytest.mark.parametrize("args", [["display", "bogus"], ["display", "on", "bogus"], ["display", "off", "now"],
                                  ["display", "99x1"], ["display", "on", "1920x1080", "x"]])
def test_linux_display_bad_arguments(tmp_path, args):
    env, calls, _, _ = fake_vkms(tmp_path)
    r = run([LINUX] + args, tmp_path, env=env)
    assert r.returncode == 1 and "usage: awake display" in r.stdout
    assert not calls.exists()
