r"""Jungle Hawks 2.5 WT installer - downloads the mod parts from git and puts them into <IL-2>\MODS as JSGME folders.

* Each part = one git repo (components.json): the base WT pack, the Aces of Thunder swapper (only when "I own Aces of
  Thunder" is ticked), and the optional vanilla Impact FX / Better BoX AI / Heavy Gun Sounds mods.
* Download: git (shallow clone / fetch of one branch) into %LOCALAPPDATA%\JH_Installer\repos\<id>; without git, the
  branch zip from GitHub. The repo's mod\ folder is copied into MODS (never the .git folder).
* Update check (like the Plotting Table): at start, the installed commit of each part is compared with the head of its
  branch (git ls-remote, or the GitHub API without git). Nothing updates by itself: the line shows
  "Installed - Update avail" and the user presses Install / Update.
* A MODS folder that JSGME has enabled (MODS\!INSTLOGS\<name> install.log) is never written: disable it first.
Python 3.10+ standard library only. Start: double-click jh_installer.pyw (or Start JH Installer.bat).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
VERSION = (HERE / "VERSION").read_text().strip() if (HERE / "VERSION").exists() else "0.1.0"
HOME = Path(os.environ.get("JH_INSTALLER_HOME") or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "JH_Installer")
STATE = HOME / "state.json"
LOG = HOME / "installer.log"
GAME_DIR_NAME = "IL-2 Sturmovik Battle of Stalingrad"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def log(msg):
    HOME.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


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


# ------------------------------------------------------------------ game folder
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


# ------------------------------------------------------------------ git / http
def have_git():
    return shutil.which("git") is not None


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, creationflags=NO_WINDOW)
    if r.returncode:
        raise RuntimeError(f"{' '.join(cmd)}\n{r.stderr.strip()}")
    return r.stdout


def gh_parts(url):
    m = re.match(r"https://github\.com/([^/]+)/([^/.]+)", url)
    return (m.group(1), m.group(2)) if m else None


def remote_head(comp):
    """commit at the head of the component's branch, or None when it cannot be read (offline, no repo yet)."""
    url, br = comp["repo"], comp.get("branch", "main")
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
    except Exception as e:  # noqa: BLE001 - any failure = unknown, the line keeps its state
        log(f"update check {comp['id']}: {e}")
        return None


def fetch(comp, progress):
    """bring the repo to the branch head in the cache; return (checkout dir, commit)."""
    url, br = comp["repo"], comp.get("branch", "main")
    dst = HOME / "repos" / comp["id"]
    if have_git():
        if (dst / ".git").exists():
            progress("fetching")
            run(["git", "fetch", "--depth", "1", "origin", br], cwd=dst)
            run(["git", "reset", "--hard", "FETCH_HEAD"], cwd=dst)
        else:
            if dst.exists():
                shutil.rmtree(dst)
            dst.parent.mkdir(parents=True, exist_ok=True)
            progress("cloning")
            run(["git", "clone", "--depth", "1", "--branch", br, url, str(dst)])
        if (dst / ".gitattributes").exists() and "lfs" in (dst / ".gitattributes").read_text(errors="replace"):
            progress("large files")
            run(["git", "lfs", "pull"], cwd=dst)
        return dst, run(["git", "rev-parse", "HEAD"], cwd=dst).strip()
    gp = gh_parts(url)
    if not gp:
        raise RuntimeError("git is not installed and the repo is not on GitHub - install Git for Windows")
    head = remote_head(comp)
    progress("downloading zip")
    tmp = Path(tempfile.mkdtemp(prefix="jhinst_"))
    zp = tmp / "src.zip"
    urllib.request.urlretrieve(f"https://github.com/{gp[0]}/{gp[1]}/archive/refs/heads/{br}.zip", zp)
    with zipfile.ZipFile(zp) as z:
        z.extractall(tmp / "x")
    inner = next((tmp / "x").iterdir())
    if dst.exists():
        shutil.rmtree(dst)
    shutil.move(str(inner), dst)
    shutil.rmtree(tmp, ignore_errors=True)
    return dst, head or "zip"


def copy_mod(src_root, mods, progress):
    """copy every folder under <repo>\\mod into MODS (folder by folder, temp + rename)."""
    names = []
    for d in sorted((src_root / "mod").iterdir()):
        if not d.is_dir():
            continue
        target = Path(mods) / d.name
        if jsgme_enabled(mods, d.name):
            raise RuntimeError(f'"{d.name}" is enabled in JSGME - disable it there, then press Install / Update again')
        progress(f"copying {d.name}")
        tmp = Path(mods) / (d.name + ".jhinst_tmp")
        if tmp.exists():
            shutil.rmtree(tmp)
        shutil.copytree(d, tmp)
        if target.exists():
            shutil.rmtree(target)
        os.replace(tmp, target)
        names.append(d.name)
    return names


# ------------------------------------------------------------------ install logic (no GUI; used by the tests too)
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
        missing = [n for n in st.get("folders", []) if not (self.mods / n).exists()]
        if missing:
            return "Not installed (folder removed)"
        if head and st.get("commit") not in (head, "zip"):
            return "Installed - Update avail"
        return "Installed"

    def install(self, comp, progress=lambda s: None):
        if comp.get("waiting"):
            raise RuntimeError("this part is not released yet")
        src, commit = fetch(comp, progress)
        folders = copy_mod(src, self.mods, progress) if (src / "mod").exists() else []
        if comp.get("after_install"):
            # tool parts (Aces swapper): start the tool; it builds its overlay folder in MODS itself
            progress("starting the builder")
            cmd = [c.replace("{repo}", str(src)).replace("{game}", str(self.game)) for c in comp["after_install"]]
            subprocess.Popen(cmd, cwd=src)
        self.state[comp["id"]] = {"commit": commit, "folders": folders, "installed": time.strftime("%Y-%m-%d %H:%M"),
                                  "repo": comp["repo"], "branch": comp.get("branch", "main")}
        save_state(self.state)
        log(f"installed {comp['id']} {commit} -> {folders}")
        return folders


# ------------------------------------------------------------------ GUI
def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    cfg = load_json(HERE / "components.json", {})
    comps = cfg.get("components", [])
    root = tk.Tk()
    root.title(f"Jungle Hawks 2.5 WT - Installer {VERSION}")
    root.geometry("900x560")
    root.configure(bg="#10201a")
    st = ttk.Style(root)
    st.theme_use("clam")
    for w in ("TFrame", "TLabel", "TCheckbutton"):
        st.configure(w, background="#10201a", foreground="#e8efe9")
    st.configure("Treeview", rowheight=26)
    frm = ttk.Frame(root, padding=14)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text="Jungle Hawks 2.5 WT", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ttk.Label(frm, text="Downloads the mod parts and puts them into the game's MODS folder. Enable them in JSGME.",
              wraplength=860).pack(anchor="w", pady=(0, 8))

    gvar = tk.StringVar(value=str(find_game() or load_json(STATE, {}).get("_game", "")))
    row = ttk.Frame(frm)
    row.pack(fill="x")
    ttk.Label(row, text="IL-2 folder:").pack(side="left")
    ttk.Entry(row, textvariable=gvar, width=90).pack(side="left", padx=6, fill="x", expand=True)
    ttk.Button(row, text="Browse...", command=lambda: gvar.set(filedialog.askdirectory() or gvar.get())).pack(side="left")

    aces = tk.BooleanVar(value=bool(load_json(STATE, {}).get("_aces", False)))
    vanilla = tk.BooleanVar(value=bool(load_json(STATE, {}).get("_vanilla", False)))
    ttk.Checkbutton(frm, text="I own Aces of Thunder (adds the cockpit / WT asset swapper as an overlay on the base pack)",
                    variable=aces, command=lambda: refresh()).pack(anchor="w", pady=(8, 0))
    ttk.Checkbutton(frm, text="Also install the vanilla versions of Impact FX, Better BoX AI and Heavy Gun Sounds "
                              "(for the stock game, not together with Jungle Hawks)",
                    variable=vanilla, command=lambda: refresh()).pack(anchor="w")

    tree = ttk.Treeview(frm, columns=("part", "status", "folder"), show="headings", height=9)
    for c, w in (("part", 420), ("status", 200), ("folder", 240)):
        tree.heading(c, text=c.capitalize())
        tree.column(c, width=w)
    tree.pack(fill="both", expand=True, pady=10)
    msg = tk.StringVar(value="")
    ttk.Label(frm, textvariable=msg, wraplength=860).pack(anchor="w")
    heads = {}

    def visible():
        out = []
        for c in comps:
            g = c.get("group", "base")
            if g == "aces" and not aces.get():
                continue
            if g == "vanilla" and not vanilla.get():
                continue
            out.append(c)
        return out

    def refresh():
        inst = Installer(comps, gvar.get() or None)
        tree.delete(*tree.get_children())
        for c in visible():
            status = inst.status(c, heads.get(c["id"])) if inst.game else "Pick the IL-2 folder"
            tree.insert("", "end", iid=c["id"], values=(c["name"], status, ", ".join(c.get("folders", []))))

    def check_updates():
        for c in comps:
            if not c.get("waiting") and c["id"] in load_json(STATE, {}):
                heads[c["id"]] = remote_head(c)
        root.after(0, refresh)

    def do_install():
        game = gvar.get()
        if not game or not (Path(game) / "bin" / "game").exists():
            messagebox.showerror("JH Installer", "Pick the IL-2 Great Battles folder (the one with bin\\game).")
            return
        sel = [c for c in visible() if not c.get("waiting")]
        picked = set(tree.selection())
        if picked:
            sel = [c for c in sel if c["id"] in picked]
        inst = Installer(comps, game)
        sel = [c for c in sel if picked or inst.status(c, heads.get(c["id"])) != "Installed"]
        if not sel:
            msg.set("Nothing to do: every shown part is installed and current.")
            return
        st_ = load_json(STATE, {})
        st_.update({"_game": game, "_aces": aces.get(), "_vanilla": vanilla.get()})
        save_state(st_)

        def work():
            errs = []
            for c in sel:
                try:
                    Installer(comps, game).install(c, lambda s, c=c: root.after(0, msg.set, f"{c['name']}: {s}"))
                    heads[c["id"]] = load_json(STATE, {})[c["id"]]["commit"]
                except Exception as e:  # noqa: BLE001
                    errs.append(f"{c['name']}: {e}")
                    log(f"install {c['id']} failed: {e}")
            root.after(0, refresh)
            root.after(0, msg.set, "Done. Enable the folders in JSGME (base pack first, overlays after)." if not errs
                       else "Problems:\n" + "\n".join(errs))
        threading.Thread(target=work, daemon=True).start()

    bar = ttk.Frame(frm)
    bar.pack(fill="x")
    ttk.Button(bar, text="Install / Update", command=do_install).pack(side="left")
    ttk.Button(bar, text="Check for updates",
               command=lambda: threading.Thread(target=check_updates, daemon=True).start()).pack(side="left", padx=8)
    ttk.Label(bar, text="Select lines to reinstall only those. Nothing updates by itself.").pack(side="left", padx=8)
    refresh()
    threading.Thread(target=check_updates, daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        import selftest
        sys.exit(selftest.main())
    gui()
