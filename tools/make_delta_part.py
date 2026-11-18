r"""Ship a new build as one extra release part on top of the previous build's parts (no full re-upload).
usage: python -I make_delta_part.py "<new mod folder>" "<previous parts dir>" <out dir> <new version tag>
Compares the new folder with the previous manifest's folder (same MODS parent): every new or changed file goes into
one extra zip (under the PREVIOUS folder name, so it unpacks over the earlier parts), the manifest lists the old
parts + the delta part and sets install_as = the new folder name. Files deleted since the previous build go into the
manifest's "remove" list; the installer deletes them after unpacking.
Upload the delta part + the new manifest.json to the release; the earlier parts stay as they are.
"""
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def tree(root):
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file()}


def main():
    new, prev, out, tag = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
    man = json.loads((prev / "manifest.json").read_text(encoding="utf-8"))
    old = new.parent / man["folder"]
    a, b = tree(old), tree(new)
    gone = sorted(set(a) - set(b))
    changed = sorted(r for r in b if r not in a or a[r].stat().st_size != b[r].stat().st_size or sha(a[r]) != sha(b[r]))
    out.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9._-]", "", man["folder"].replace(" ", "_"))
    n = len(man["parts"]) + 1
    zp = out / f"{stem}.part{n:02d}_{tag}_delta.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for r in changed:
            z.write(b[r], f"{man['folder']}/{r}")
    man["parts"].append({"name": zp.name, "bytes": zp.stat().st_size, "sha256": sha(zp), "files": len(changed),
                         "delta": True})
    man.update(version=tag, install_as=new.name, files=len(b))
    if gone:
        man["remove"] = gone
    (out / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    for p in man["parts"][:-1]:                    # the unchanged parts, for a local test of the full set
        if not (out / p["name"]).exists() and (prev / p["name"]).exists():
            try:
                (out / p["name"]).hardlink_to(prev / p["name"])
            except OSError:
                shutil.copyfile(prev / p["name"], out / p["name"])
    print(f"{len(changed)} changed/new files -> {zp.name} ({zp.stat().st_size / 1e6:.1f} MB); manifest {tag}, "
          f"install_as {new.name}")
    for r in changed:
        print("  " + r)
    for r in gone:
        print("  removed: " + r)


if __name__ == "__main__":
    main()
