r"""Jungle Hawks installer - downloads the mod parts and puts them into <IL-2>\MODS as JSGME folders.

Player's path: forum post -> GitHub README -> Releases -> this installer -> tick the parts -> Install / Update
(progress bar + log) -> JSGME found or installed, MODS created, folders copied -> Setup tab: "enable modes = 1"
and, for Aces of Thunder owners, a separate window that downloads the Cockpit Overlay Builder.

* Each part = one git repo (components.json). Download: git (shallow clone / fetch of the release branch) into
  %LOCALAPPDATA%\JH_Installer\repos\<id>; without git, the branch zip from GitHub. Only the repo's mod\ folders are
  copied into MODS, never .git.
* Update check (like the Plotting Table, but on the git branch): at start the installed commit is compared with the
  head of the branch. Nothing updates by itself; the line shows "Installed - Update avail".
* A MODS folder JSGME has enabled (MODS\!INSTLOGS\<name> install.log) is never written.
Python 3.10+ standard library only. Start: Start JH Installer.bat (or double-click this file).
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
VERSION = (HERE / "VERSION").read_text().strip() if (HERE / "VERSION").exists() else "0.2.0"
HOME = Path(os.environ.get("JH_INSTALLER_HOME") or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "JH_Installer")
STATE = HOME / "state.json"
LOG = HOME / "installer.log"
GAME_DIR_NAME = "IL-2 Sturmovik Battle of Stalingrad"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
_log_sink = []          # GUI adds a callback here; every log line also goes to installer.log


def log(msg):
    HOME.mkdir(parents=True, exist_ok=True)
    line = time.strftime("%H:%M:%S ") + msg
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d ") + line + "\n")
    for cb in _log_sink:
        cb(line)


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_state(state):
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
    os.replace(tmp, STATE)


# ------------------------------------------------------------------ game folder, JSGME, startup.cfg
def steam_libraries():
    libs = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            steam = Path(winreg.QueryValueEx(k, "SteamPath")[0])
        libs.append(steam)
        vdf = steam / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            libs += [Path(m.replace("\\\\", "\\")) for m in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text(errors="replace"))]
    except OSError:
        pass
    return list(dict.fromkeys(libs))


def find_game():
    for lib in steam_libraries():
        p = lib / "steamapps" / "common" / GAME_DIR_NAME
        if (p / "bin" / "game").exists():
            return p
    return None


def jsgme_enabled(mods, folder):
    return (Path(mods) / "!INSTLOGS" / f"{folder} install.log").exists()


def jsgme_present(game):
    return (Path(game) / "JSGME.exe").exists()


def ensure_mods(game):
    m = Path(game) / "MODS"
    if not m.exists():
        m.mkdir()
        log(f"created {m}")
    return m


def install_jsgme(game, url, progress):
    """download JSGME (zip holding JSGME.exe, or JSGME.exe itself) into the IL-2 folder."""
    if jsgme_present(game):
        log("JSGME already in the IL-2 folder")
        return True
    if not url:
        log("JSGME not in the IL-2 folder - not needed: the launcher mounts Jungle Hawks itself with JSGME's own "
            "files (MODS\\!INSTLOGS, !BACKUP). Install JSGME yourself if you also want to use it.")
        return False
    tmp = Path(tempfile.mkdtemp(prefix="jhinst_jsgme_"))
    dst = tmp / Path(url.split("?")[0]).name
    http_get(url, dst, progress, "JSGME")
    if dst.suffix.lower() == ".zip":
        with zipfile.ZipFile(dst) as z:
            exe = next((n for n in z.namelist() if n.lower().endswith("jsgme.exe")), None)
            if not exe:
                raise RuntimeError("the JSGME download has no JSGME.exe")
            (Path(game) / "JSGME.exe").write_bytes(z.read(exe))
    elif dst.name.lower() == "jsgme.exe":
        shutil.copyfile(dst, Path(game) / "JSGME.exe")
    else:                               # an installer (jsgme_setup.exe): run it, the player picks the IL-2 folder
        log("starting the JSGME setup - install it into the IL-2 folder")
        subprocess.run([str(dst)], cwd=tmp)
    shutil.rmtree(tmp, ignore_errors=True)
    ok = jsgme_present(game)
    log("JSGME installed" if ok else "JSGME.exe still not in the IL-2 folder")
    return ok


def modes_state(game):
    cfg = Path(game) / "data" / "startup.cfg"
    if not cfg.exists():
        return None
    m = re.search(r"\[KEY = system\](.*?)\[END\]", cfg.read_text(encoding="latin-1"), re.S)
    v = re.search(r"^\s*modes\s*=\s*(\d+)", m.group(1), re.M) if m else None
    return int(v.group(1)) if v else 0


def enable_modes(game):
    """set modes = 1 in [KEY = system] of data\\startup.cfg (the game's switch for loose mod files); backup first."""
    cfg = Path(game) / "data" / "startup.cfg"
    raw = cfg.read_bytes().decode("latin-1")
    nl = "\r\n" if "\r\n" in raw else "\n"
    m = re.search(r"\[KEY = system\](.*?)\[END\]", raw, re.S)
    if not m:
        raise RuntimeError("data\\startup.cfg has no [KEY = system] section - start the game once, then try again")
    body = m.group(1)
    if re.search(r"^\s*modes\s*=", body, re.M):
        body2 = re.sub(r"^(\s*modes\s*=\s*)\d+", r"\g<1>1", body, flags=re.M)
    else:
        body2 = body.rstrip("\r\n") + nl + "\tmodes = 1" + nl
    if body2 == body:
        log("modes = 1 already set")
        return
    bak = cfg.with_name("startup.cfg.bak_jhinstaller")
    if not bak.exists():
        shutil.copyfile(cfg, bak)
    tmp = cfg.with_suffix(".tmp_jh")
    tmp.write_bytes((raw[:m.start(1)] + body2 + raw[m.end(1):]).encode("latin-1"))
    os.replace(tmp, cfg)
    log(f"modes = 1 set in {cfg} (backup: {bak.name})")


GBML_NAME = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
GBML_SWITCHES = (("multiplayer", "handshake", "MP handshake"), ("multiplayer", "strict", "Refuse mismatched hosts"),
                 ("multiplayer", "kick", "Kick mismatched players"))


def gbml_ini(game):
    """the gbml.ini the launcher mounts: the JH folder's own copy in MODS (the live bin\\game one is overwritten on mount)"""
    mod = jh_mod_folder(game)
    return Path(game) / "MODS" / mod / "bin" / "game" / "gbml.ini" if mod else None


def gbml_plugins(text):
    """[plugins] lines in order -> [(name, on, note)]; note = the ; lines just above. First line wins, like the loader."""
    out, notes, inside = [], [], False
    for line in re.split(r"\r\n|\n|\r", text):
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            inside, notes = s[1:-1].strip().lower() == "plugins", []
            continue
        if not inside:
            continue
        if s.startswith((";", "#")):
            notes.append(s.lstrip(";#").strip())
            continue
        k, eq, v = s.partition("=")
        k = k.strip()
        if eq and GBML_NAME.match(k) and not any(n.lower() == k.lower() for n, _, _ in out):
            out.append((k, v.strip() == "1", " ".join(notes)))
        notes = []
    return out


def gbml_value(text, section, key, default="1"):
    inside = False
    for line in re.split(r"\r\n|\n|\r", text):
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            inside = s[1:-1].strip().lower() == section.lower()
        elif inside and not s.startswith((";", "#")):
            k, eq, v = s.partition("=")
            if eq and k.strip().lower() == key.lower():
                return v.strip()
    return default


def gbml_set(text, section, key, value):
    """change one value in gbml.ini; notes, order, spacing and newlines stay. Missing key/section is appended."""
    if not GBML_NAME.match(key) or any(ch in value for ch in "\r\n[];="):
        raise ValueError("invalid gbml.ini setting")
    nl = "\r\n" if "\r\n" in text else "\n"
    lines, inside, last = re.split(r"\r\n|\n|\r", text), False, -1
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            inside = s[1:-1].strip().lower() == section.lower()
            if inside:
                last = i
            continue
        if not inside:
            continue
        if s:
            last = i
        if s.startswith((";", "#")):
            continue
        m = re.match(r"^(\s*" + re.escape(key) + r"\s*=\s*)(.*?)(\s*)$", line, re.I)
        if m:
            lines[i] = m.group(1) + value + m.group(3)
            return nl.join(lines)
    if last >= 0:
        lines.insert(last + 1, f"{key}={value}")
        return nl.join(lines)
    end = len(lines)
    while end and not lines[end - 1].strip():
        end -= 1
    lines[end:end] = [f"[{section}]", f"{key}={value}"]
    return nl.join(lines)


def gbml_save(game, changes):
    """changes = {(section, key): "0"/"1"}. Writes the JH folder's gbml.ini (first save keeps gbml.ini.bak_jhlauncher);
    a mounted copy in bin\\game that matches it is updated too, so the change counts without remounting."""
    if il2_running():
        raise RuntimeError("Close IL-2 before changing plugins.")
    src = gbml_ini(game)
    if not src or not src.exists():
        raise RuntimeError("No gbml.ini in the Jungle Hawks folder in MODS - install Jungle Hawks first.")
    raw = src.read_bytes()
    text = raw.decode("utf-8-sig")
    new = text
    for (section, key), value in changes.items():
        if gbml_value(new, section, key, None) != value:
            new = gbml_set(new, section, key, value)
    if new == text:
        return "No plugin changes to save."
    bom = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
    live = Path(game) / "bin" / "game" / "gbml.ini"
    targets = [src] + ([live] if live.exists() and live.read_bytes() == raw else [])
    bak = src.with_name("gbml.ini.bak_jhlauncher")
    if not bak.exists():
        shutil.copyfile(src, bak)
    for t in targets:
        tmp = t.with_suffix(".tmp_jh")
        tmp.write_bytes(bom + new.encode("utf-8"))
        os.replace(tmp, t)
    log(f"gbml.ini plugins saved: {', '.join(f'{k}={v}' for (_, k), v in changes.items())} -> "
        f"{', '.join(str(t) for t in targets)}")
    return "Plugins saved" + (" (also in the mounted copy)" if len(targets) > 1 else "") + f". Backup: {bak.name}"


def gbml_last_launch(game):
    """(fingerprint, blocked reason) of the last loader start in bin\\game\\gbml_log.txt"""
    p = Path(game) / "bin" / "game" / "gbml_log.txt"
    fp, blocked = "", ""
    if p.exists():
        for line in p.read_text(encoding="latin-1", errors="replace").splitlines():
            if "[gbml] ---- GB Mod Loader" in line and "starting" in line:
                fp, blocked = "", ""
            m = re.search(r"\[gbml-mp\] fingerprint (GBML1:[0-9a-f]+)", line)
            if m:
                fp = m.group(1)
            if "MULTIPLAYER BLOCKED: " in line:
                blocked = line.split("MULTIPLAYER BLOCKED: ", 1)[1]
    return fp, blocked


SHORTCUT_NAME = "Il2∶ Jungle Hawks"          # U+2236 RATIO: Windows file names cannot hold ':'


def create_shortcut(desktop=None):
    """Desktop shortcut that opens the launcher window (jh_installer.pyw, Play page) with pythonw, icon = the IL-2 Great
    Battles badge (art/jh_launch.ico). jh_launch.pyw stays for a headless start (mount, play, restore) from a script."""
    desktop = Path(desktop or Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop")
    pyw = Path(sys.executable).with_name("pythonw.exe")
    if not pyw.exists():
        pyw = Path(sys.executable)
    lnk = desktop / f"{SHORTCUT_NAME}.lnk"
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:JH_LNK);"
          "$s.TargetPath=$env:JH_PYW;$s.Arguments=[char]34+$env:JH_LAUNCH+[char]34;$s.WorkingDirectory=$env:JH_DIR;"
          "$s.IconLocation=$env:JH_ICO+',0';$s.Description='IL-2: Jungle Hawks';$s.Save()")
    tmp = desktop / "jh_shortcut_tmp.lnk"           # PowerShell 5 mangles non-ASCII names: save ASCII, then rename
    env = dict(os.environ, JH_LNK=str(tmp), JH_PYW=str(pyw), JH_LAUNCH=str(HERE / "jh_installer.pyw"), JH_DIR=str(HERE),
               JH_ICO=str(HERE / "art" / "jh_launch.ico"))
    r = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], env=env,
                       capture_output=True, text=True, creationflags=NO_WINDOW)
    if r.returncode or not tmp.exists():
        raise RuntimeError("shortcut not created: " + (r.stderr or r.stdout).strip()[:200])
    os.replace(tmp, lnk)
    log(f"Desktop shortcut created: {lnk}")
    return lnk


# ------------------------------------------------------------------ play: mount through JSGME, start IL-2, restore
STEAM_RUN = "steam://rungameid/307960"


def jh_mod_folder(game):
    """the Jungle Hawks folder in MODS to mount: an enabled one first, else the installer's, else the newest WT / 2.5"""
    import jsgme
    mods = Path(game) / "MODS"
    names = [d.name for d in mods.iterdir() if d.is_dir() and not d.name.startswith("!")] if mods.is_dir() else []
    jh = [n for n in names if "jungle hawks" in n.lower()]
    for n in jh:
        if jsgme.is_enabled(game, n):
            return n
    st = load_json(STATE, {})
    for cid in ("jh_wt", "jh_base"):
        for f in st.get(cid, {}).get("folders", []):
            if f in names:
                return f

    def ver(n):
        import re as _re
        m = _re.search(r"WT (\d+(?:\.\d+)?)$", n)
        return float(m.group(1)) if m else (0.5 if n in ("Jungle Hawks 2.5", "Pingu's Jungle Hawks v2.5") else 0.0)
    jh.sort(key=ver)
    return jh[-1] if jh else None


def il2_running():
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Il-2.exe", "/NH"], capture_output=True, text=True,
                       creationflags=NO_WINDOW)
    return "Il-2.exe" in r.stdout


def play(game, unload_after=True, progress=lambda m, p=None: None, wait=True):
    """mount JH through the JSGME routine (unless already enabled), start IL-2 via Steam, wait for the game to close,
    then disable JH again - only if this run enabled it (a JSGME-enabled JH stays as the player left it)."""
    import jsgme
    mod = jh_mod_folder(game)
    if not mod:
        raise RuntimeError("no Jungle Hawks folder in MODS - install it first")
    if il2_running():
        raise RuntimeError("IL-2 is already running - close it first")
    mounted_here = False
    if not jsgme.is_enabled(game, mod):
        others = [m for m in jsgme.enabled(game) if "jungle hawks" in m.lower()]
        if others:
            raise RuntimeError(f"another Jungle Hawks folder is enabled in JSGME: {others[0]} - unload it first")
        jsgme.activate(game, mod, log=log, progress=progress)
        mounted_here = True
        if unload_after:                      # remembered, so a closed / crashed launcher restores on its next start
            st = load_json(STATE, {})
            st["_mounted_by_launcher"] = {"game": str(game), "mod": mod}
            save_state(st)
    log(f"play: starting IL-2 with {mod}")
    os.startfile(STEAM_RUN)
    if not wait:
        return mod, mounted_here
    for _ in range(90):                       # up to 3 minutes for Steam to start the game
        if il2_running():
            break
        time.sleep(2)
    else:
        log("play: IL-2 did not start within 3 minutes")
    progress("IL-2 is running - Jungle Hawks will be unloaded when the game closes" if (mounted_here and unload_after)
             else "IL-2 is running", None)
    while il2_running():
        time.sleep(5)
    log("play: IL-2 closed")
    if mounted_here and unload_after:
        jsgme.deactivate(game, mod, log=log, progress=progress)
        _forget_mount()
    return mod, mounted_here


def _forget_mount():
    st = load_json(STATE, {})
    if st.pop("_mounted_by_launcher", None) is not None:
        save_state(st)


def recover(progress=lambda m, p=None: None):
    """a launcher-mounted JH still enabled while IL-2 is closed (launcher closed or crashed mid-game): restore it"""
    import jsgme
    m = load_json(STATE, {}).get("_mounted_by_launcher")
    if not m or il2_running():
        return None
    if jsgme.is_enabled(m["game"], m["mod"]):
        log(f"recover: {m['mod']} was mounted by the launcher and IL-2 is closed - restoring the game files")
        jsgme.deactivate(m["game"], m["mod"], log=log, progress=progress)
    _forget_mount()
    return m["mod"]


def unload(game, progress=lambda m, p=None: None):
    """disable every enabled Jungle Hawks folder through the JSGME routine (originals come back from !BACKUP)"""
    import jsgme
    if il2_running():
        raise RuntimeError("close IL-2 first")
    done = []
    for m in reversed(jsgme.enabled(game)):
        if "jungle hawks" in m.lower():
            jsgme.deactivate(game, m, log=log, progress=progress)
            done.append(m)
    _forget_mount()
    if not done:
        log("unload: no Jungle Hawks folder is enabled")
    return done


# ------------------------------------------------------------------ git / http with progress
def have_git():
    return shutil.which("git") is not None


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, creationflags=NO_WINDOW)
    if r.returncode:
        raise RuntimeError(f"{' '.join(cmd)}\n{r.stderr.strip()}")
    return r.stdout


GIT_PCT = re.compile(r"(Counting|Compressing|Receiving|Resolving|Updating files|Filtering content)[^:]*:\s+(\d+)%")
GIT_W = {"Counting": (0, 5), "Compressing": (5, 10), "Receiving": (10, 80), "Resolving": (80, 90),
         "Updating files": (90, 97), "Filtering content": (90, 97)}


def run_git_progress(cmd, cwd, progress, what):
    """git with --progress: stderr lines -> progress(msg, pct)."""
    p = subprocess.Popen(cmd, cwd=cwd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True,
                         creationflags=NO_WINDOW, bufsize=1)
    buf, last, err = "", None, []
    while True:
        ch = p.stderr.read(1)
        if not ch:
            break
        if ch in "\r\n":
            line, buf = buf.strip(), ""
            if not line:
                continue
            m = GIT_PCT.search(line)
            if m:
                a, b = GIT_W[m.group(1)]
                pct = a + (b - a) * int(m.group(2)) / 100
                progress(f"{what}: {line}", pct)
                if m.group(1) != last:
                    log(f"{what}: {m.group(1).lower()}")
                    last = m.group(1)
            else:
                err.append(line)
                log(f"{what}: {line}")
        else:
            buf += ch
    if p.wait():
        raise RuntimeError(f"{' '.join(cmd[:3])} failed: " + " | ".join(err[-3:]))


def http_get(url, dst, progress, what):
    req = urllib.request.Request(url, headers={"User-Agent": "JH-Installer"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dst, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        while True:
            b = r.read(1 << 16)
            if not b:
                break
            f.write(b)
            got += len(b)
            progress(f"{what}: {got / 1e6:.1f} MB" + (f" of {total / 1e6:.1f} MB" if total else ""),
                     80 * got / total if total else None)
    log(f"{what}: downloaded {got / 1e6:.1f} MB")


def gh_parts(url):
    m = re.match(r"https://github\.com/([^/]+)/([^/.]+)", url)
    return (m.group(1), m.group(2)) if m else None


def remote_head(comp):
    if comp.get("source") == "release_assets":
        return remote_version(comp)
    """commit at the head of the part's branch, or None when it cannot be read (offline, repo not published yet)."""
    url, br = comp["repo"], comp.get("branch", "release")
    try:
        if have_git():
            out = run(["git", "ls-remote", url, f"refs/heads/{br}"])
            return out.split()[0] if out.strip() else None
        gp = gh_parts(url)
        if not gp:
            return None
        req = urllib.request.Request(f"https://api.github.com/repos/{gp[0]}/{gp[1]}/commits/{br}",
                                     headers={"Accept": "application/vnd.github.sha", "User-Agent": "JH-Installer"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode().strip()
    except Exception as e:  # noqa: BLE001 - any failure = unknown; the line keeps its state
        log(f"update check {comp['id']}: {str(e).splitlines()[0][:160]}")
        return None


def fetch(comp, progress=lambda m, p=None: None):
    """bring the part's repo to the branch head in the cache; return (checkout dir, commit)."""
    url, br, name = comp["repo"], comp.get("branch", "release"), comp["name"]
    dst = HOME / "repos" / comp["id"]
    if have_git():
        if (dst / ".git").exists():
            log(f"{name}: fetching {br}")
            run_git_progress(["git", "fetch", "--progress", "--depth", "1", "origin", br], dst, progress, name)
            run(["git", "reset", "--hard", "FETCH_HEAD"], cwd=dst)
        else:
            if dst.exists():
                shutil.rmtree(dst)
            dst.parent.mkdir(parents=True, exist_ok=True)
            log(f"{name}: cloning {url} ({br})")
            run_git_progress(["git", "clone", "--progress", "--depth", "1", "--branch", br, url, str(dst)], None,
                             progress, name)
        if (dst / ".gitattributes").exists() and "lfs" in (dst / ".gitattributes").read_text(errors="replace"):
            log(f"{name}: large files (Git LFS)")
            progress(f"{name}: large files", 90)
            run(["git", "lfs", "pull"], cwd=dst)
        return dst, run(["git", "rev-parse", "HEAD"], cwd=dst).strip()
    gp = gh_parts(url)
    if not gp:
        raise RuntimeError("git is not installed and the repo is not on GitHub - install Git for Windows")
    head = remote_head(comp)
    tmp = Path(tempfile.mkdtemp(prefix="jhinst_"))
    zp = tmp / "src.zip"
    http_get(f"https://github.com/{gp[0]}/{gp[1]}/archive/refs/heads/{br}.zip", zp, progress, name)
    progress(f"{name}: unpacking", 85)
    with zipfile.ZipFile(zp) as z:
        z.extractall(tmp / "x")
    inner = next((tmp / "x").iterdir())
    if dst.exists():
        shutil.rmtree(dst)
    shutil.move(str(inner), dst)
    shutil.rmtree(tmp, ignore_errors=True)
    return dst, head or "zip"


def copy_mod(src_root, mods, progress=lambda m, p=None: None):
    """copy every folder under <repo>\\mod into MODS (folder by folder, temp + rename), with progress by file."""
    names = []
    dirs = [d for d in sorted((src_root / "mod").iterdir()) if d.is_dir()]
    files = [f for d in dirs for f in d.rglob("*") if f.is_file()]
    done = 0
    for d in dirs:
        if jsgme_enabled(mods, d.name):
            raise RuntimeError(f'"{d.name}" is enabled in JSGME - disable it there, then press Install / Update again')
        target, tmp = Path(mods) / d.name, Path(mods) / (d.name + ".jhinst_tmp")
        if tmp.exists():
            shutil.rmtree(tmp)
        log(f"copying {d.name} into MODS")
        for f in d.rglob("*"):
            if f.is_file():
                out = tmp / f.relative_to(d)
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, out)
                done += 1
                if done % 25 == 0 or done == len(files):
                    progress(f"copying {d.name}: {done} of {len(files)} files", 97 + 3 * done / max(1, len(files)))
        if target.exists():
            shutil.rmtree(target)
        os.replace(tmp, target)
        names.append(d.name)
    return names


# ------------------------------------------------------------------ install logic (no GUI; the selftest uses it)
# ------------------------------------------------------------------ release-asset parts (the big main pack)
PARALLEL = 3          # parts downloaded at once
RETRIES = 4


class NoAccess(RuntimeError):
    """the release cannot be read with the current GitHub sign-in (private repo, no token, no invite)"""


def github_token():
    """installer setting, else GITHUB_TOKEN / GH_TOKEN, else the GitHub CLI's sign-in (testers with gh)"""
    tok = load_json(STATE, {}).get("_gh_token") or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok.strip()
    if shutil.which("gh"):
        try:
            r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10, creationflags=NO_WINDOW)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except Exception:  # noqa: BLE001
            pass
    return None


class _DropAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """GitHub asset downloads redirect to object storage, which refuses a second Authorization header"""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and urllib.parse.urlparse(newurl).netloc != urllib.parse.urlparse(req.full_url).netloc:
            new.headers.pop("Authorization", None)
            new.unredirected_hdrs.pop("Authorization", None)
        return new


_OPENER = urllib.request.build_opener(_DropAuthOnRedirect)


def gh_open(url, headers=None, timeout=60, private=False):
    h = {"User-Agent": "JH-Installer", **(headers or {})}
    tok = github_token() if private else None
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    try:
        return _OPENER.open(urllib.request.Request(url, headers=h), timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 404) and private:
            raise NoAccess(f"no access to {url.split('/repos/')[-1].split('/releases')[0]} (HTTP {e.code})") from None
        raise


def assets_manifest(comp):
    """manifest.json of the part's release: local folder (comp['assets_dir'], tests) or the GitHub release
    comp.get('tag', 'latest'). -> (manifest dict, {part name: url or local path})"""
    if comp.get("assets_dir"):
        d = Path(comp["assets_dir"])
        man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        return man, {pp["name"]: str(d / pp["name"]) for pp in man["parts"]}
    gp = gh_parts(comp["repo"])
    tag = comp.get("tag", "latest")
    api = (f"https://api.github.com/repos/{gp[0]}/{gp[1]}/releases/latest" if tag == "latest"
           else f"https://api.github.com/repos/{gp[0]}/{gp[1]}/releases/tags/{tag}")
    priv = bool(comp.get("private"))
    with gh_open(api, {"Accept": "application/vnd.github+json"}, 30, priv) as r:
        rel = json.loads(r.read().decode())
    # private repos: download through the API asset URL (works with the token); public: the browser URL
    urls = {a["name"]: (("api:" + a["url"]) if priv else a["browser_download_url"]) for a in rel.get("assets", [])}
    if "manifest.json" not in urls:
        raise RuntimeError(f"release {rel.get('tag_name')} has no manifest.json")
    with _open_asset(urls["manifest.json"]) as r:
        man = json.loads(r.read().decode())
    missing = [pp["name"] for pp in man["parts"] if pp["name"] not in urls]
    if missing:
        raise RuntimeError("release is missing parts: " + ", ".join(missing))
    return man, urls


def _open_asset(url, extra=None):
    if url.startswith("api:"):
        return gh_open(url[4:], {"Accept": "application/octet-stream", **(extra or {})}, 60, True)
    return gh_open(url, extra or {}, 60, False)


def _get_part(src, dst, size, got_cb):
    """one part with resume (HTTP Range on a .partial file) and retries; local paths are copied (tests)."""
    tmp = dst.with_suffix(dst.suffix + ".partial")
    for attempt in range(1, RETRIES + 1):
        try:
            if not str(src).startswith(("http", "api:")):
                shutil.copyfile(src, tmp)
                got_cb(dst.name, tmp.stat().st_size)
            else:
                have = tmp.stat().st_size if tmp.exists() else 0
                hdr = {"User-Agent": "JH-Installer"}
                if have:
                    hdr["Range"] = f"bytes={have}-"
                with _open_asset(src, {k: v for k, v in hdr.items() if k != "User-Agent"}) as r:
                    mode = "ab" if have and r.status == 206 else "wb"
                    have = have if mode == "ab" else 0
                    with open(tmp, mode) as f:
                        while True:
                            b = r.read(1 << 20)
                            if not b:
                                break
                            f.write(b)
                            have += len(b)
                            got_cb(dst.name, have)
            if size and tmp.stat().st_size != size:
                raise RuntimeError(f"size {tmp.stat().st_size} != {size}")
            os.replace(tmp, dst)
            return
        except Exception as e:  # noqa: BLE001
            log(f"{dst.name}: attempt {attempt} failed ({str(e)[:120]})" + (", retrying" if attempt < RETRIES else ""))
            if attempt == RETRIES:
                raise
            time.sleep(2 * attempt)


def fetch_assets(comp, progress=lambda m, p=None: None):
    """download every part of the release (PARALLEL at once, resume + retry), verify sha256, unpack all parts into
    one folder -> (folder holding mod/<name>, version tag). One progress bar: download 0-85 %, unpack 85-97 %."""
    from concurrent.futures import ThreadPoolExecutor
    man, urls = assets_manifest(comp)
    cache = HOME / "assets" / comp["id"]
    cache.mkdir(parents=True, exist_ok=True)
    total = sum(pp["bytes"] for pp in man["parts"]) or 1
    got, lock = {}, threading.Lock()
    todo = []
    for pp in man["parts"]:
        f = cache / pp["name"]
        if f.exists() and f.stat().st_size == pp["bytes"] and sha_file(f) == pp["sha256"]:
            got[pp["name"]] = pp["bytes"]            # already here from an earlier run
        else:
            todo.append(pp)
    log(f"{comp['name']} {man['version']}: {len(man['parts'])} parts, {total / 1e9:.2f} GB"
        + (f", {len(man['parts']) - len(todo)} already downloaded" if len(todo) < len(man['parts']) else ""))

    def got_cb(name, n):
        with lock:
            got[name] = n
            done = sum(got.values())
        progress(f"{comp['name']}: downloading {done / 1e9:.2f} of {total / 1e9:.2f} GB "
                 f"({len(man['parts'])} parts, {PARALLEL} at a time)", 85 * done / total)

    with ThreadPoolExecutor(max_workers=PARALLEL) as ex:
        futs = [ex.submit(_get_part, urls[pp["name"]], cache / pp["name"], pp["bytes"], got_cb) for pp in todo]
        for fu in futs:
            fu.result()
    for pp in man["parts"]:
        if sha_file(cache / pp["name"]) != pp["sha256"]:
            (cache / pp["name"]).unlink()
            raise RuntimeError(f"{pp['name']}: checksum mismatch - deleted, press Install / Update again")
    log(f"{comp['name']}: all parts verified")
    out = HOME / "repos" / comp["id"]
    if out.exists():
        shutil.rmtree(out)
    (out / "mod").mkdir(parents=True)
    for i, pp in enumerate(man["parts"], 1):
        progress(f"{comp['name']}: unpacking part {i} of {len(man['parts'])}", 85 + 12 * (i - 1) / len(man["parts"]))
        with zipfile.ZipFile(cache / pp["name"]) as z:     # in manifest order: a delta part overwrites
            z.extractall(out / "mod")
    for r in man.get("remove", []):                   # delta release: files deleted since the earlier parts
        f = out / "mod" / man["folder"] / r
        if f.is_file():
            f.unlink()
    if man.get("install_as") and man["install_as"] != man["folder"]:   # delta release: earlier parts + changed files
        os.replace(out / "mod" / man["folder"], out / "mod" / man["install_as"])
    return out, man["version"]


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def remote_version(comp):
    """release tag for asset parts (update check)"""
    try:
        return assets_manifest(comp)[0]["version"]
    except Exception as e:  # noqa: BLE001
        log(f"update check {comp['id']}: {str(e)[:160]}")
        return None


class Installer:
    def __init__(self, components, game):
        self.components = components
        self.game = Path(game) if game else None
        self.state = load_json(STATE, {})

    @property
    def mods(self):
        return self.game / "MODS"

    def status(self, comp, head=None):
        st = self.state.get(comp["id"])
        if comp.get("waiting"):
            return "Waiting - not released yet"
        if not st:
            return "Not installed"
        if [n for n in st.get("folders", []) if not (self.mods / n).exists()]:
            return "Not installed (folder removed)"
        if head and st.get("commit") not in (head, "zip"):
            return "Installed - Update avail"
        return "Installed"

    def install(self, comp, progress=lambda m, p=None: None):
        if comp.get("waiting"):
            raise RuntimeError("this part is not released yet")
        ensure_mods(self.game)
        src, commit = (fetch_assets if comp.get("source") == "release_assets" else fetch)(comp, progress)
        folders = copy_mod(src, self.mods, progress) if (src / "mod").exists() else []
        self.state[comp["id"]] = {"commit": commit, "folders": folders, "installed": time.strftime("%Y-%m-%d %H:%M"),
                                  "repo": comp["repo"], "branch": comp.get("branch", "release"), "path": str(src)}
        save_state(self.state)
        log(f"{comp['name']}: installed {commit[:10]} -> {', '.join(folders) or 'tool folder'}")
        progress(f"{comp['name']}: done", 100)
        return folders


# ------------------------------------------------------------------ GUI
def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    cfg = load_json(HERE / "components.json", {})
    comps = cfg.get("components", [])
    tool = cfg.get("cockpit_builder", {})
    BG, FG, ACC = "#10201a", "#e8efe9", "#3f8f52"
    root = tk.Tk()
    root.title(f"Pingu's Jungle Hawks v2.5 - Installer {VERSION}")
    root.geometry("940x860")
    root.minsize(860, 620)
    root.configure(bg=BG)
    st = ttk.Style(root)
    st.theme_use("clam")
    for w in ("TFrame", "TLabel", "TCheckbutton", "TLabelframe", "TLabelframe.Label"):
        st.configure(w, background=BG, foreground=FG)
    st.configure("TNotebook", background=BG)
    st.configure("TNotebook.Tab", padding=(14, 6))
    st.configure("Treeview", rowheight=26)
    st.configure("green.Horizontal.TProgressbar", background=ACC)
    saved = load_json(STATE, {})

    art = {}
    if (HERE / "art" / "banner.png").exists():          # the mod's own loading-screen art
        art["main"] = tk.PhotoImage(file=str(HERE / "art" / "banner.png"))
        tk.Label(root, image=art["main"], bd=0, bg=BG).pack(fill="x")
    head = ttk.Frame(root, padding=(14, 8, 14, 0))
    head.pack(fill="x")
    if not art:
        ttk.Label(head, text="Jungle Hawks", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ttk.Label(head, text="Downloads the mod, puts it into the game's MODS folder, and gets JSGME ready.").pack(anchor="w")
    gvar = tk.StringVar(value=str(find_game() or saved.get("_game", "")))

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=14, pady=10)
    tab_i, tab_s = ttk.Frame(nb, padding=10), ttk.Frame(nb, padding=10)
    nb.add(tab_i, text="Install")
    nb.add(tab_s, text="Settings")

    # --- Install tab
    ttk.Label(tab_i, text="Select what to install (Ctrl+click for more than one). The standalones are for the stock game, "
                          "not for use together with Jungle Hawks.", wraplength=860).pack(anchor="w")
    tree = ttk.Treeview(tab_i, columns=("part", "status", "folder"), show="headings", height=5, selectmode="extended")
    for c, w in (("part", 430), ("status", 190), ("folder", 230)):
        tree.heading(c, text=c.capitalize())
        tree.column(c, width=w)
    tree.pack(fill="x", pady=8)
    bar = ttk.Frame(tab_i)
    bar.pack(fill="x")
    pvar = tk.DoubleVar(value=0)
    pmsg = tk.StringVar(value="Ready.")
    ttk.Progressbar(tab_i, variable=pvar, maximum=100, style="green.Horizontal.TProgressbar").pack(fill="x", pady=(10, 2))
    ttk.Label(tab_i, textvariable=pmsg).pack(anchor="w")
    lf = ttk.Labelframe(tab_i, text="Log", padding=4)
    lf.pack(fill="both", expand=True, pady=(6, 0))
    logbox = tk.Text(lf, height=10, bg="#0b1510", fg="#cfe3d4", insertbackground=FG, relief="flat", font=("Consolas", 9))
    sb = ttk.Scrollbar(lf, command=logbox.yview)
    logbox.configure(yscrollcommand=sb.set, state="disabled")
    sb.pack(side="right", fill="y")
    logbox.pack(fill="both", expand=True)

    def to_log(line):
        def add():
            logbox.configure(state="normal")
            logbox.insert("end", line + "\n")
            logbox.see("end")
            logbox.configure(state="disabled")
        root.after(0, add)
    _log_sink.append(to_log)
    heads = {}

    def visible():
        return list(comps)

    def refresh():
        inst = Installer(comps, gvar.get() or None)
        tree.delete(*tree.get_children())
        for c in visible():
            s = inst.status(c, heads.get(c["id"])) if inst.game else "Pick the IL-2 folder"
            tree.insert("", "end", iid=c["id"], values=(c["name"], s, ", ".join(c.get("folders", []))))
        refresh_setup()

    def check_updates():
        for c in comps:
            if not c.get("waiting") and c["id"] in load_json(STATE, {}):
                heads[c["id"]] = remote_head(c)
        root.after(0, refresh)

    def progress(msg, pct=None):
        root.after(0, pmsg.set, msg)
        if pct is not None:
            root.after(0, pvar.set, pct)

    def game_ok():
        g = gvar.get()
        if not g or not (Path(g) / "bin" / "game").exists():
            messagebox.showerror("JH Installer", "Pick the IL-2 Great Battles folder (the one with bin\\game in it).")
            return None
        return g

    busy = {"on": False}

    def do_install():
        game = game_ok()
        if not game or busy["on"]:
            return
        picked = set(tree.selection())
        inst = Installer(comps, game)
        if not picked:                              # nothing selected: Jungle Hawks itself
            picked = {c["id"] for c in comps if c.get("group", "base") == "base"
                      and inst.status(c, heads.get(c["id"])) != "Installed"}
        sel = [c for c in visible() if not c.get("waiting") and c["id"] in picked]
        waiting = [c["name"] for c in visible() if c.get("waiting") and c["id"] in picked]
        for w in waiting:
            log(f"{w}: not released yet - skipped")
        if not sel:
            pmsg.set("Nothing to do: select a line, or Jungle Hawks is installed and current.")
            return
        s = load_json(STATE, {})
        s.update({"_game": game})
        save_state(s)
        busy["on"] = True

        def work():
            errs = []
            try:
                ensure_mods(game)
                if not jsgme_present(game):
                    try:
                        install_jsgme(game, cfg.get("jsgme_url", ""), progress)
                    except Exception as e:  # noqa: BLE001
                        log(f"JSGME: {e}")
                for i, c in enumerate(sel, 1):
                    log(f"--- {c['name']} ({i} of {len(sel)})")
                    try:
                        Installer(comps, game).install(c, progress)
                        heads[c["id"]] = load_json(STATE, {})[c["id"]]["commit"]
                    except Exception as e:  # noqa: BLE001
                        errs.append(f"{c['name']}: {str(e).splitlines()[0]}")
                        log(f"FAILED {c['name']}: {e}")
            finally:
                busy["on"] = False
                root.after(0, refresh)
                done = ("Done. Open JSGME (in the IL-2 folder) and enable Jungle Hawks." if not errs
                        else "Problems - see the log: " + "; ".join(errs))
                progress(done, 100 if not errs else None)
                log(done)
        threading.Thread(target=work, daemon=True).start()

    ttk.Button(bar, text="Install / Update", command=do_install).pack(side="left")
    ttk.Button(bar, text="Check for updates",
               command=lambda: threading.Thread(target=check_updates, daemon=True).start()).pack(side="left", padx=8)
    ttk.Button(bar, text="Open MODS folder",
               command=lambda: game_ok() and os.startfile(ensure_mods(gvar.get()))).pack(side="left")
    ttk.Label(bar, text="Nothing updates by itself.").pack(side="left", padx=10)

    # --- Settings tab: the paths the installer uses, and what is in place
    pbox = ttk.Labelframe(tab_s, text="Paths", padding=10)
    pbox.pack(fill="x")
    r = ttk.Frame(pbox)
    r.pack(fill="x", pady=2)
    ttk.Label(r, text="IL-2 folder", width=16).pack(side="left")
    ttk.Entry(r, textvariable=gvar).pack(side="left", padx=6, fill="x", expand=True)
    ttk.Button(r, text="Browse...", command=lambda: (gvar.set(filedialog.askdirectory() or gvar.get()), refresh())).pack(side="left")
    sv = {k: tk.StringVar() for k in ("jsgme", "mods", "modes", "cache", "logf")}
    for key, label in (("jsgme", "JSGME"), ("mods", "MODS folder"), ("modes", "startup.cfg"),
                       ("cache", "Download cache"), ("logf", "Log file")):
        r = ttk.Frame(pbox)
        r.pack(fill="x", pady=2)
        ttk.Label(r, text=label, width=16).pack(side="left")
        ttk.Label(r, textvariable=sv[key]).pack(side="left", padx=6)
    box = ttk.Labelframe(tab_s, text="Game setup", padding=10)
    box.pack(fill="x", pady=(12, 0))

    def refresh_setup():
        g = gvar.get()
        sv["cache"].set(str(HOME / "repos"))
        sv["logf"].set(str(LOG))
        if not g or not (Path(g) / "bin" / "game").exists():
            for k in ("jsgme", "mods", "modes"):
                sv[k].set("pick the IL-2 folder first")
            return
        G = Path(g)
        sv["jsgme"].set(f"{G / 'JSGME.exe'}  -  " + ("found" if jsgme_present(g) else "not found: Install JSGME below"))
        sv["mods"].set(f"{G / 'MODS'}  -  " + ("found" if (G / "MODS").exists() else "not there yet: created on install"))
        m = modes_state(g)
        sv["modes"].set(f"{G / 'data' / 'startup.cfg'}  -  " +
                        ("modes = 1 (on)" if m == 1 else ("modes off" if m == 0 else "not found: start the game once")))

    def setup_action(fn, *a):
        game = game_ok()
        if not game:
            return

        def work():
            try:
                fn(game, *a)
            except Exception as e:  # noqa: BLE001
                log(f"setup: {e}")
            root.after(0, refresh_setup)
        threading.Thread(target=work, daemon=True).start()

    btns = ttk.Frame(box)
    btns.pack(fill="x", pady=(8, 0))
    ttk.Button(btns, text="Enable modes = 1 now (needed for IL-2 mods)",
               command=lambda: setup_action(enable_modes)).pack(side="left")
    ttk.Button(btns, text="Install JSGME",
               command=lambda: setup_action(install_jsgme, cfg.get("jsgme_url", ""), progress)).pack(side="left", padx=8)
    ttk.Button(btns, text="Create MODS folder", command=lambda: setup_action(ensure_mods)).pack(side="left")
    ttk.Label(box, text="modes = 1 is written to data\\startup.cfg ([KEY = system]); the first change keeps a backup "
                        "as startup.cfg.bak_jhinstaller. Close the game first.", wraplength=820).pack(anchor="w", pady=(8, 0))

    abox = ttk.Labelframe(tab_s, text="Aces of Thunder", padding=10)
    abox.pack(fill="x", pady=(12, 0))
    aces = tk.BooleanVar(value=bool(saved.get("_aces", False)))

    def aces_ticked():
        s = load_json(STATE, {})
        s["_aces"] = aces.get()
        save_state(s)
        if aces.get():
            builder_window()
    ttk.Checkbutton(abox, text="I own Aces of Thunder / have it installed locally", variable=aces,
                    command=aces_ticked).pack(anchor="w")
    ttk.Label(abox, text="Ticking it opens a separate window for the Cockpit Overlay Builder. The tool runs on your PC and "
                         "builds its overlay from your own install.", wraplength=820).pack(anchor="w", pady=(4, 0))

    def builder_window():
        game = game_ok()
        if not game:
            return
        w = tk.Toplevel(root)
        w.title("Cockpit Overlay Builder")
        w.geometry("720x540")
        w.configure(bg=BG)
        w.transient(root)
        if (HERE / "art" / "banner_builder.png").exists():
            art["builder"] = tk.PhotoImage(file=str(HERE / "art" / "banner_builder.png"))
            tk.Label(w, image=art["builder"], bd=0, bg=BG).pack(fill="x")
        f = ttk.Frame(w, padding=14)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=tool.get("name", "Cockpit Overlay Builder"), font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(f, text=tool.get("about", ""), wraplength=680).pack(anchor="w", pady=(4, 10))
        tv, tm = tk.DoubleVar(value=0), tk.StringVar(value="")
        ttk.Progressbar(f, variable=tv, maximum=100, style="green.Horizontal.TProgressbar").pack(fill="x")
        ttk.Label(f, textvariable=tm).pack(anchor="w", pady=(2, 8))
        tlog = tk.Text(f, height=8, bg="#0b1510", fg="#cfe3d4", relief="flat", font=("Consolas", 9))
        tlog.pack(fill="both", expand=True)

        def tprog(msg, pct=None):
            w.after(0, tm.set, msg)
            if pct is not None:
                w.after(0, tv.set, pct)

        def tline(line):
            w.after(0, lambda: (tlog.insert("end", line + "\n"), tlog.see("end")))
        rb = ttk.Frame(f)
        rb.pack(fill="x", pady=(8, 0))
        start_btn = ttk.Button(rb, text="Start the tool", state="disabled")

        def start_tool():
            st_ = load_json(STATE, {}).get(tool.get("id", "builder"), {})
            p = Path(st_.get("path", ""))
            cmd = [c.replace("{repo}", str(p)).replace("{game}", game) for c in tool.get("start", [])]
            if not cmd or not p.exists():
                tline("download the tool first")
                return
            tline("starting: " + " ".join(cmd))
            subprocess.Popen(cmd, cwd=p)

        def download():
            def work():
                _log_sink.append(tline)
                try:
                    comp = dict(tool, id=tool.get("id", "builder"))
                    Installer([comp], game).install(comp, tprog)
                    w.after(0, lambda: start_btn.configure(state="normal"))
                except Exception as e:  # noqa: BLE001
                    tline(f"FAILED: {e}")
                finally:
                    _log_sink.remove(tline)
            threading.Thread(target=work, daemon=True).start()
        ttk.Button(rb, text="Download / update the tool", command=download).pack(side="left")
        start_btn.configure(command=start_tool)
        start_btn.pack(side="left", padx=8)
        if tool.get("id", "builder") in load_json(STATE, {}):
            start_btn.configure(state="normal")
            tline("already downloaded - Download / update fetches the newest release")

    refresh()
    threading.Thread(target=check_updates, daemon=True).start()
    log(f"JH Installer {VERSION} started; log file {LOG}")
    if "--smoke" in sys.argv:                       # GUI smoke test: open, draw, close
        root.after(1500, root.destroy)
    if "--shot" in sys.argv:                        # docs: screenshots of both tabs and the tool window, then close
        out = Path(sys.argv[sys.argv.index("--shot") + 1])

        def grab(win, name):
            from PIL import ImageGrab
            win.attributes('-topmost', True)
            win.lift()
            win.focus_force()
            win.update()
            time.sleep(0.4)
            x, y = win.winfo_rootx(), win.winfo_rooty()
            ImageGrab.grab((x, y, x + win.winfo_width(), y + win.winfo_height())).save(out / name)
        root.after(1800, lambda: grab(root, "installer_install.png"))
        root.after(2200, lambda: nb.select(1))
        root.after(2800, lambda: grab(root, "installer_setup.png"))
        root.after(3000, builder_window)
        root.after(3800, lambda: grab(root.winfo_children()[-1], "installer_tool.png"))
        root.after(4300, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        import selftest
        sys.exit(selftest.main())
    import ui
    ui.run()
