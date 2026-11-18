r"""Split a JSGME mod folder into release-asset zips (each < 2 GB, GitHub's per-asset limit) + manifest.json.
usage: python -I make_release_parts.py "<mod folder>" <out dir> <version tag> [--max-gb 1.9]
Each part is a normal zip holding a subset of the files under "<folder name>/..."; the installer downloads every
part listed in manifest.json, checks its sha256, unpacks them all into one folder and copies that into MODS.
Upload ALL parts + manifest.json to the GitHub release <version tag>.
"""
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    src, out, tag = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    cap = float(sys.argv[sys.argv.index("--max-gb") + 1]) if "--max-gb" in sys.argv else 1.9
    cap_b = int(cap * 1024 ** 3)
    out.mkdir(parents=True, exist_ok=True)
    files = sorted((p for p in src.rglob("*") if p.is_file()), key=lambda p: p.relative_to(src).as_posix().lower())
    parts, cur, size = [], [], 0
    for f in files:
        s = f.stat().st_size
        if cur and size + s > cap_b:
            parts.append(cur)
            cur, size = [], 0
        cur.append(f)
        size += s                      # stored size bound: compression only makes a part smaller
    if cur:
        parts.append(cur)
    stem = src.name.replace(" ", "_")
    man = {"version": tag, "folder": src.name, "files": len(files), "parts": []}
    for i, group in enumerate(parts, 1):
        zp = out / f"{stem}.part{i:02d}.zip"
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
            for f in group:
                z.write(f, f"{src.name}/{f.relative_to(src).as_posix()}")
        man["parts"].append({"name": zp.name, "bytes": zp.stat().st_size, "sha256": sha(zp), "files": len(group)})
        print(f"{zp.name}: {len(group)} files, {zp.stat().st_size / 1e9:.2f} GB")
    (out / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(f"{len(parts)} parts + manifest.json in {out}")


if __name__ == "__main__":
    main()
