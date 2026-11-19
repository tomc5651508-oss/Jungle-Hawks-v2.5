r"""Headless JSGME: enable / disable a mod folder exactly the way JSGME does, with JSGME's own files, so a player can
switch between JSGME and the JH launcher at any time.

JSGME state (read from a live install, 18 Nov 2026):
  <game>\MODS\<mod>\...                    the mod folder (stays complete; files are COPIED into the game)
  <game>\MODS\!INSTLOGS\<mod> install.log  one line per installed path, CRLF: 'NEWFLDR|dir\' for a folder the mod created,
                                           'dir\file' for a file, '\file' for a file in the game root
  <game>\MODS\!BACKUP\<path>.<mod>         the game's previous file, saved when <mod> overwrote it
  <game>\MODS\JSGME.ini                    [DEPENDANCIES] <earlier mod>="<later mod>" (later mod overwrote its files)
                                           [MODS] <mod>=<activation order>
Enable  : skips a top-level 'documentation' folder (JSGME's rule). For every file: back up an existing game file to !BACKUP\<path>.<mod> (and record a dependency when that file
          came from another enabled mod), copy the mod file, log it; new folders logged as NEWFLDR first.
Disable : refused while a later mod depends on this one. For every logged file: delete it, move its backup back;
          remove the folders this mod created (deepest first, only if empty); delete the log; update JSGME.ini.
Every step is written to the JH installer log. Files are copied in chunks (no whole-file reads).

Mount speed (JH launcher only): when the mod folder and the game are on the same drive, files are hard-linked instead
of copied (12 GB mounts in seconds, no second copy on disk). Text/config files (.ini .cfg .txt .json .db .xml .log) are
always real copies, because the game and tools write those in place and a write would reach the mod folder. Disabling
works the same either way (JSGME deletes the game-side name and moves the backup back), so JSGME can disable a mod the
launcher enabled and the other way round.
"""
import os
import shutil
import time
from pathlib import Path


def _lp(p):
    """Windows extended-length path: mod files can be deeper than 260 characters (MODS\\<mod>\\data\\scg\\...)"""
    p = Path(p)
    if os.name != "nt" or str(p).startswith("\\\\?\\"):
        return p
    s = os.path.abspath(str(p))
    return Path("\\\\?\\UNC\\" + s[2:]) if s.startswith("\\\\") else Path("\\\\?\\" + s)


class JSGMEError(RuntimeError):
    pass


COPY_ALWAYS = {".ini", ".cfg", ".txt", ".json", ".db", ".xml", ".log"}


def _place(s, dst, link):
    if link and s.suffix.lower() not in COPY_ALWAYS:
        try:
            os.link(s, dst)
            return
        except OSError:
            pass
    shutil.copyfile(s, dst)


def _ini_read(p):
    sec, data, order = None, {"DEPENDANCIES": [], "MODS": []}, []
    if p.exists():
        for line in p.read_text(encoding="latin-1").splitlines():
            s = line.strip()
            if s.startswith("[") and s.endswith("]"):
                sec = s[1:-1]
                data.setdefault(sec, [])
                order.append(sec)
            elif sec and "=" in s:
                k, v = s.split("=", 1)
                data[sec].append((k, v))
    return data


def _ini_write(p, data):
    out = []
    for sec in ("DEPENDANCIES", "MODS"):
        out.append(f"[{sec}]")
        out += [f"{k}={v}" for k, v in data.get(sec, [])]
    for sec, rows in data.items():
        if sec not in ("DEPENDANCIES", "MODS") and rows:
            out.append(f"[{sec}]")
            out += [f"{k}={v}" for k, v in rows]
    tmp = p.with_suffix(".ini.jhtmp")
    tmp.write_bytes(("\r\n".join(out) + "\r\n").encode("latin-1"))
    os.replace(tmp, p)


def enabled(game):
    """[MODS] names in activation order"""
    d = _ini_read(Path(game) / "MODS" / "JSGME.ini")
    return [k for k, v in sorted(d["MODS"], key=lambda kv: int(kv[1]) if kv[1].isdigit() else 0)]


def is_enabled(game, mod):
    return (Path(game) / "MODS" / "!INSTLOGS" / f"{mod} install.log").exists()


def _log_lines(game, mod):
    p = Path(game) / "MODS" / "!INSTLOGS" / f"{mod} install.log"
    return p.read_text(encoding="latin-1").splitlines() if p.exists() else []


def _owner(game, rel, skip):
    """the enabled mod whose install.log lists rel (JSGME path form), else None"""
    logs = Path(game) / "MODS" / "!INSTLOGS"
    for f in logs.glob("* install.log") if logs.is_dir() else []:
        name = f.name[:-len(" install.log")]
        if name != skip and rel in f.read_text(encoding="latin-1").splitlines():
            return name
    return None


def activate(game, mod, log=print, progress=lambda m, p=None: None, link=True):
    game = _lp(game)
    mods = game / "MODS"
    src = mods / mod
    if not src.is_dir():
        raise JSGMEError(f"mod folder not found: {src}")
    if is_enabled(game, mod):
        log(f"JSGME: {mod} is already enabled")
        return
    (mods / "!INSTLOGS").mkdir(exist_ok=True)
    (mods / "!BACKUP").mkdir(exist_ok=True)
    lines, deps = [], set()
    files = []
    owners = {}                                   # path -> enabled mod that installed it (one pass over the logs)
    for f in (mods / "!INSTLOGS").glob("* install.log"):
        name = f.name[:-len(" install.log")]
        for l in f.read_text(encoding="latin-1").splitlines():
            if l and not l.startswith("NEWFLDR|"):
                owners[l] = name
    for dp, dn, fn in os.walk(src):
        d = Path(dp)
        rel_d = d.relative_to(src)
        if str(rel_d) == ".":                     # JSGME leaves a top-level documentation folder in MODS
            dn[:] = [x for x in dn if x.lower() != "documentation"]
        if str(rel_d) != "." and not (game / rel_d).exists():
            lines.append(f"NEWFLDR|{str(rel_d)}\\")
            (game / rel_d).mkdir(parents=True, exist_ok=True)
        for f in sorted(fn):
            files.append((d / f, rel_d / f))
    same = link and os.stat(src).st_dev == os.stat(game).st_dev
    need = sum(s.stat().st_size for s, _ in files if not (same and s.suffix.lower() not in COPY_ALWAYS))
    free = shutil.disk_usage(game).free
    if need > free - 512 * 2**20:
        for l in reversed(lines):                 # nothing copied yet: take the empty folders back out
            try:
                (game / l[len("NEWFLDR|"):].rstrip("\\")).rmdir()
            except OSError:
                pass
        raise JSGMEError(f"not enough free space on the game drive: {need / 2**30:.1f} GB needed, "
                         f"{free / 2**30:.1f} GB free")
    log(f"JSGME: enabling {mod} ({len(files)} files, {'hard links + copies' if same else 'copies'}, "
        f"{need / 2**30:.2f} GB copied)")
    logp = mods / "!INSTLOGS" / f"{mod} install.log"
    with open(logp.with_suffix(".log.jhtmp"), "wb") as lf:
        for line in lines:
            lf.write((line + "\r\n").encode("latin-1"))
        for i, (s, rel) in enumerate(files, 1):
            jrel = ("\\" + rel.name) if str(rel.parent) == "." else str(rel)
            dst = game / rel
            if dst.exists():
                bak = mods / "!BACKUP" / rel.parent / f"{rel.name}.{mod}"
                bak.parent.mkdir(parents=True, exist_ok=True)
                if bak.exists():
                    bak.unlink()
                os.replace(dst, bak)
                other = owners.get(jrel)
                if other:
                    deps.add(other)
            _place(s, dst, same)
            lf.write((jrel + "\r\n").encode("latin-1"))
            if i % 200 == 0 or i == len(files):
                progress(f"Mounting {mod}: {i} of {len(files)} files", 100 * i / len(files))
    os.replace(logp.with_suffix(".log.jhtmp"), logp)
    ini = mods / "JSGME.ini"
    d = _ini_read(ini)
    nxt = max([int(v) for k, v in d["MODS"] if v.isdigit()] + [0]) + 1
    d["MODS"] = [kv for kv in d["MODS"] if kv[0] != mod] + [(mod, str(nxt))]
    dep = dict(d["DEPENDANCIES"])
    for other in deps:
        cur = dep.get(other, "")
        names = [x for x in cur.strip('"').split('","') if x] if cur else []
        if mod not in names:
            names.append(mod)
        dep[other] = '"' + '","'.join(names) + '"'
    d["DEPENDANCIES"] = list(dep.items())
    _ini_write(ini, d)
    log(f"JSGME: {mod} enabled (log {logp.name}, {len(deps)} dependency/ies)")


def dependants(game, mod):
    d = _ini_read(Path(game) / "MODS" / "JSGME.ini")
    for k, v in d["DEPENDANCIES"]:
        if k == mod:
            return [x for x in v.strip('"').split('","') if x and is_enabled(game, x)]
    return []


def deactivate(game, mod, log=print, progress=lambda m, p=None: None):
    game = _lp(game)
    mods = game / "MODS"
    if not is_enabled(game, mod):
        log(f"JSGME: {mod} is not enabled")
        return
    later = dependants(game, mod)
    if later:
        raise JSGMEError(f"{mod} cannot be disabled while these are enabled after it: {', '.join(later)} "
                         "(disable them first, as JSGME requires)")
    lines = _log_lines(game, mod)
    files = [l for l in lines if l and not l.startswith("NEWFLDR|")]
    folders = [l[len("NEWFLDR|"):].rstrip("\\") for l in lines if l.startswith("NEWFLDR|")]
    log(f"JSGME: disabling {mod} ({len(files)} files)")
    failed = []
    for i, jrel in enumerate(files, 1):
        rel = Path(jrel.lstrip("\\"))
        dst = game / rel
        bak = mods / "!BACKUP" / rel.parent / f"{rel.name}.{mod}"
        for attempt in range(4):              # a file the game / AV still holds: retry, then keep it in the log
            try:
                if dst.exists():
                    dst.unlink()
                if bak.exists():
                    os.replace(bak, dst)
                break
            except OSError as e:
                if attempt == 3:
                    failed.append(jrel)
                    log(f"JSGME: could not restore {jrel}: {e}")
                else:
                    time.sleep(0.5)
        if i % 200 == 0 or i == len(files):
            progress(f"Unloading {mod}: {i} of {len(files)} files", 100 * i / len(files))
    if failed:                                # keep JSGME state honest: the log lists what is still in the game
        logp = mods / "!INSTLOGS" / f"{mod} install.log"
        tmp = logp.with_suffix(".log.jhtmp2")
        tmp.write_bytes(("".join(l + "\r\n" for l in failed)).encode("latin-1"))
        os.replace(tmp, logp)
        raise JSGMEError(f"{len(failed)} file(s) of {mod} could not be restored (in use?). Close IL-2 and anything "
                         f"using the game folder, then press Revert to vanilla again. First: {failed[0]}")
    for f in sorted(folders, key=lambda s: s.count("\\"), reverse=True):
        p = game / f
        try:
            p.rmdir()
        except OSError:
            pass
    (mods / "!INSTLOGS" / f"{mod} install.log").unlink()
    ini = mods / "JSGME.ini"
    d = _ini_read(ini)
    d["MODS"] = [kv for kv in d["MODS"] if kv[0] != mod]
    dep = []
    for k, v in d["DEPENDANCIES"]:
        if k == mod:
            continue
        names = [x for x in v.strip('"').split('","') if x and x != mod]
        if names:
            dep.append((k, '"' + '","'.join(names) + '"'))
    d["DEPENDANCIES"] = dep
    _ini_write(ini, d)
    log(f"JSGME: {mod} disabled, originals restored")


def all_enabled(game):
    """every mod JSGME or the launcher left in the game: JSGME.ini order, plus install logs the ini does not list
    (an ini lost or out of step), plus a half-written launcher log (.log.jhtmp: a mount that stopped part-way)"""
    mods = Path(game) / "MODS"
    logs = mods / "!INSTLOGS"
    if not logs.is_dir():
        return []
    for t in logs.glob("* install.log.jhtmp"):    # partial mount: promote its log so deactivate can undo it
        real = t.with_name(t.name[:-len(".jhtmp")])
        if not real.exists():
            os.replace(t, real)
    have = [f.name[:-len(" install.log")] for f in logs.glob("* install.log")]
    order = [m for m in enabled(game) if m in have]
    return [m for m in have if m not in order] + order


def orphan_backups(game):
    """!BACKUP files whose mod has no install log any more (their originals never went back)"""
    mods = Path(game) / "MODS"
    root = mods / "!BACKUP"
    if not root.is_dir():
        return []
    names = sorted((d.name for d in mods.iterdir() if d.is_dir() and not d.name.startswith("!")),
                   key=len, reverse=True)
    out = []
    for dp, dn, fn in os.walk(_lp(root)):
        for f in fn:
            for m in names:
                if f.endswith("." + m) and not is_enabled(game, m):
                    rel = Path(dp).relative_to(_lp(root)) / f[:-len(m) - 1]
                    out.append((root / rel.parent / f, rel, m))
                    break
    return out
