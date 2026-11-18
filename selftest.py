r"""Offline test of the installer logic with local repos (file URLs), a fake game folder and a temp HOME.
usage: python -I jh_installer.pyw --selftest   (or python -I selftest.py)
Checks: install copies mod\ into MODS without .git; status Installed; a new commit upstream -> "Installed - Update avail"
(update check, no auto-update); a JSGME-enabled folder is refused; Install again -> Installed.
"""
import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def git(cwd, *a):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="jhinst_test_"))
    os.environ["JH_INSTALLER_HOME"] = str(tmp / "home")
    spec = importlib.util.spec_from_file_location("jhi", HERE / "jh_installer.pyw",
                                                  loader=importlib.machinery.SourceFileLoader("jhi", str(HERE / "jh_installer.pyw")))
    jhi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(jhi)
    up = tmp / "upstream"
    (up / "mod" / "Test Mod" / "data").mkdir(parents=True)
    (up / "mod" / "Test Mod" / "data" / "a.txt").write_text("v1")
    git(up, "init", "-b", "main")
    git(up, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init")
    git(up, "add", "-A")
    git(up, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "v1")
    game = tmp / "game"
    (game / "bin" / "game").mkdir(parents=True)
    (game / "MODS" / "!INSTLOGS").mkdir(parents=True)
    comp = {"id": "t", "name": "Test", "repo": up.as_uri(), "branch": "main", "folders": ["Test Mod"]}
    ok = []

    inst = jhi.Installer([comp], game)
    assert inst.status(comp) == "Not installed"
    inst.install(comp)
    f = game / "MODS" / "Test Mod" / "data" / "a.txt"
    assert f.read_text() == "v1" and not (game / "MODS" / "Test Mod" / ".git").exists()
    head = jhi.remote_head(comp)
    assert jhi.Installer([comp], game).status(comp, head) == "Installed"
    ok.append("install + Installed")

    (up / "mod" / "Test Mod" / "data" / "a.txt").write_text("v2")
    git(up, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "v2")
    head2 = jhi.remote_head(comp)
    assert head2 != head
    assert jhi.Installer([comp], game).status(comp, head2) == "Installed - Update avail"
    assert f.read_text() == "v1", "must not update by itself"
    ok.append("update flagged, nothing changed")

    log = game / "MODS" / "!INSTLOGS" / "Test Mod install.log"
    log.write_text("x")
    try:
        jhi.Installer([comp], game).install(comp)
        raise AssertionError("enabled folder was written")
    except RuntimeError as e:
        assert "enabled in JSGME" in str(e)
    assert f.read_text() == "v1"
    log.unlink()
    ok.append("JSGME-enabled folder refused")

    jhi.Installer([comp], game).install(comp)
    assert f.read_text() == "v2" and jhi.Installer([comp], game).status(comp, head2) == "Installed"
    ok.append("manual update")
    shutil.rmtree(tmp, ignore_errors=True)
    print("selftest OK:", "; ".join(ok))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
