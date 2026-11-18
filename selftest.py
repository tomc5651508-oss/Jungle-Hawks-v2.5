r"""Offline test of the installer logic with local repos (file URLs), a fake game folder and a temp HOME.
usage: python -I jh_installer.pyw --selftest   (or python -I selftest.py)
Checks: install copies mod\ into MODS without .git; status Installed; a new commit upstream -> "Installed - Update avail"
(update check, no auto-update); a JSGME-enabled folder is refused; Install again -> Installed.
"""
import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
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

    seen = []
    jhi.Installer([comp], game).install(comp, lambda m, p=None: seen.append(p))
    assert f.read_text() == "v2" and jhi.Installer([comp], game).status(comp, head2) == "Installed"
    assert any(p == 100 for p in seen), "progress reaches 100"
    ok.append("manual update with progress")

    (game / "data").mkdir()
    cfg = game / "data" / "startup.cfg"
    cfg.write_bytes(b"\r\n[KEY = sound]\r\n\tvolume = 1\r\n[END]\r\n\r\n[KEY = system]\r\n\tlog = 0\r\n[END]\r\n")
    assert jhi.modes_state(game) == 0
    jhi.enable_modes(game)
    assert jhi.modes_state(game) == 1 and (game / "data" / "startup.cfg.bak_jhinstaller").exists()
    assert b"[KEY = sound]\r\n\tvolume = 1" in cfg.read_bytes() and b"\tmodes = 1\r\n[END]" in cfg.read_bytes()
    cfg.write_bytes(cfg.read_bytes().replace(b"modes = 1", b"modes = 0"))
    jhi.enable_modes(game)
    assert jhi.modes_state(game) == 1 and cfg.read_bytes().count(b"modes") == 1
    ok.append("modes = 1 (added, then 0 -> 1, backup kept)")

    g2 = tmp / "game2"
    (g2 / "bin" / "game").mkdir(parents=True)
    assert not (g2 / "MODS").exists()
    jhi.Installer([comp], g2).install(comp)
    assert (g2 / "MODS" / "Test Mod" / "data" / "a.txt").exists()
    assert jhi.install_jsgme(g2, "", lambda m, p=None: None) is False
    ok.append("MODS created on install; JSGME missing reported")

    # release-asset parts (the big main pack): split, then install from a local "release"
    pack = tmp / "pack" / "Jungle Hawks 2.5"
    for i in range(7):
        (pack / "data" / f"f{i}.bin").parent.mkdir(parents=True, exist_ok=True)
        (pack / "data" / f"f{i}.bin").write_bytes(os.urandom(3000 + i))
    rel = tmp / "release"
    tool = Path(__file__).resolve().parent / "tools" / "make_release_parts.py"
    if tool.exists():
        subprocess.run([sys.executable, "-I", str(tool), str(pack), str(rel), "v2.5.0", "--max-gb", "0.000006"],
                       check=True, capture_output=True)
        comp2 = {"id": "jh_base", "name": "Jungle Hawks 2.5", "source": "release_assets", "assets_dir": str(rel),
                 "repo": "https://github.com/x/y", "folders": ["Jungle Hawks 2.5"]}
        seen2 = []
        jhi.Installer([comp2], game).install(comp2, lambda m, p=None: seen2.append(p))
        for i in range(7):
            assert (game / "MODS" / "Jungle Hawks 2.5" / "data" / f"f{i}.bin").read_bytes() == \
                (pack / "data" / f"f{i}.bin").read_bytes()
        assert jhi.Installer([comp2], game).status(comp2, jhi.remote_head(comp2)) == "Installed"
        nparts = len(json.loads((rel / "manifest.json").read_text())["parts"])
        assert nparts >= 3, nparts
        ok.append(f"release-asset parts: {nparts} parts downloaded {jhi.PARALLEL} at a time, verified, joined")
    shutil.rmtree(tmp, ignore_errors=True)
    print("selftest OK:", "; ".join(ok))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
