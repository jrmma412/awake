"""Checks that run without a desktop: syntax, versions, time parsing, safe commands, install/uninstall.
Linux tests run on Linux, macOS tests on macOS (CI runs both)."""
import ast
import os
import re
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
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"))
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
    assert run([LINUX, "status"], tmp_path).stdout.strip() == "OFF"
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
    r = run([installed, "uninstall", "-y"], tmp_path, env={"PATH": path})
    assert r.returncode == 0, r.stdout + r.stderr
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
