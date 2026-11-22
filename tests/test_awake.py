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
    # AWAKE_LID_CONF: never read the real /etc/systemd/logind.conf.d (a file there would change the output).
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
               AWAKE_LID_CONF=str(home / "awake-lid.conf"))
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
    r = run([installed, "uninstall", "-y"], tmp_path, env={"PATH": path})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "keep your lid setting" in r.stdout and (tmp_path / "awake-lid.conf").exists()
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


@linux_only
def test_linux_display_is_mac_only(tmp_path):
    assert "macOS-only" in run([LINUX, "display"], tmp_path).stdout


@mac_only
@pytest.mark.parametrize("plist", ["sh.brew.vdisplay.plist", "homebrew.mxcl.vdisplay.plist"])
def test_mac_display_sees_login_item(tmp_path, plist):
    env, _ = fake_vdisplay(tmp_path, 0)
    agents = tmp_path / "Library" / "LaunchAgents"
    agents.mkdir(parents=True)
    (agents / plist).write_text("<plist/>")
    assert "starts at login" in run([MAC, "display", "status"], tmp_path, env=env).stdout
