r"""offline tests for jsgme.py on a temp game folder (+ read-only parse of a real JSGME log if present)"""
import hashlib, os, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import jsgme as J


def h(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def snap(root):
    return {str(p.relative_to(root)): h(p) for p in Path(root).rglob("*") if p.is_file() and "MODS" not in p.parts}


def main():
    tmp = Path(tempfile.mkdtemp(prefix="jsgme_t_"))
    g = tmp / "game"
    (g / "bin" / "game").mkdir(parents=True)
    (g / "data").mkdir()
    (g / "bin" / "game" / "winmm.dll").write_bytes(b"stock-free?")
    (g / "data" / "startup.cfg").write_text("orig cfg")
    (g / "MODS").mkdir()
    A = g / "MODS" / "Mod A"; B = g / "MODS" / "Mod B"
    for m, txt in ((A, "A"), (B, "B")):
        (m / "bin" / "game" / "gbml").mkdir(parents=True)
        (m / "bin" / "game" / "winmm.dll").write_text("winmm " + txt)
        (m / "bin" / "game" / "gbml" / f"{txt}.dll").write_text(txt)
        (m / f"README {txt}.txt").write_text(txt)
    (A / "data" / "new").mkdir(parents=True); (A / "data" / "new" / "x.txt").write_text("x")
    (A / "data" / "new" / "m.dds").write_bytes(b"dds")
    before = snap(g)
    q = lambda *a, **k: None
    J.activate(g, "Mod A", log=q)
    assert (g / "bin/game/winmm.dll").read_text() == "winmm A"
    assert (g / "MODS/!BACKUP/bin/game/winmm.dll.Mod A").read_bytes() == b"stock-free?"
    log = (g / "MODS/!INSTLOGS/Mod A install.log").read_text(encoding="latin-1").splitlines()
    assert "\\README A.txt" in log and "bin\\game\\winmm.dll" in log and any(l.startswith("NEWFLDR|data\\new") for l in log)
    assert os.stat(g / "data/new/m.dds").st_nlink == 2, "dds not hard-linked"
    assert os.stat(g / "data/new/x.txt").st_nlink == 1, "txt must be a real copy"
    J.activate(g, "Mod B", log=q, link=False)
    assert J.dependants(g, "Mod A") == ["Mod B"]
    try:
        J.deactivate(g, "Mod A", log=q); raise AssertionError("A disabled under B")
    except J.JSGMEError:
        pass
    J.deactivate(g, "Mod B", log=q)
    assert (g / "bin/game/winmm.dll").read_text() == "winmm A"
    J.deactivate(g, "Mod A", log=q)
    assert snap(g) == before, "game not restored byte for byte"
    assert (A / "data/new/m.dds").read_bytes() == b"dds" and os.stat(A / "data/new/m.dds").st_nlink == 1
    assert not (g / "data/new").exists()
    assert J.enabled(g) == []
    ini = (g / "MODS/JSGME.ini").read_text()
    assert "[MODS]" in ini and "Mod A" not in ini
    shutil.rmtree(tmp)
    real = Path(r"M:\SteamLibrary\steamapps\common\IL-2 Sturmovik Battle of Stalingrad")
    msg = ""
    if (real / "MODS" / "JSGME.ini").exists():
        en = J.enabled(real)
        n = {m: sum(1 for l in J._log_lines(real, m) if l and not l.startswith("NEWFLDR|")) for m in en}
        msg = f"; real install read-only: enabled {n}"
    print("jsgme tests OK: activate/backup/log/NEWFLDR, dependency refusal, ordered disable, byte-exact restore, hard links for assets / copies for text" + msg)


main()
