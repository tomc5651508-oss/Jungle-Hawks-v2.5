r"""offline test: full parts of build A + delta part for build B -> the installer's fetch_assets gives exactly build B"""
import importlib.machinery
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
T = Path(tempfile.mkdtemp(prefix="jh_delta_"))
mods = T / "MODS"
A, B = mods / "Mod - WT 1", mods / "Mod - WT 2"
for root, txt in ((A, "old"), (B, "new")):
    (root / "data" / "x").mkdir(parents=True)
    (root / "data" / "x" / "same.bin").write_bytes(b"s" * 5000)
    (root / "data" / "x" / "changed.txt").write_text(txt)
(B / "data" / "x" / "added.txt").write_text("added")
(A / "data" / "x" / "gone.txt").write_text("removed in B")
py = sys.executable
subprocess.run([py, "-I", str(HERE / "tools/make_release_parts.py"), str(A), str(T / "p1"), "v1", "--max-gb", "0.000003"],
               check=True, capture_output=True)
subprocess.run([py, "-I", str(HERE / "tools/make_delta_part.py"), str(B), str(T / "p1"), str(T / "p2"), "v2"],
               check=True, capture_output=True)
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("jhi", HERE / "jh_installer.pyw",
                                              loader=importlib.machinery.SourceFileLoader("jhi", str(HERE / "jh_installer.pyw")))
J = importlib.util.module_from_spec(spec)
spec.loader.exec_module(J)
J.HOME = T / "home"
J.log = lambda m: None
out, ver = J.fetch_assets({"id": "t", "name": "t", "assets_dir": str(T / "p2")})
got = {p.relative_to(out / "mod").as_posix(): p.read_bytes() for p in (out / "mod").rglob("*") if p.is_file()}
want = {f"{B.name}/{p.relative_to(B).as_posix()}": p.read_bytes() for p in B.rglob("*") if p.is_file()}
assert ver == "v2" and got == want, (ver, sorted(got), sorted(want))
print(f"delta test OK: {len(got)} files = build B, folder {B.name}")
