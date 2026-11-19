r"""IL-2: Jungle Hawks launcher (the Desktop shortcut runs this).

1. Finds the IL-2 folder (installer state, else Steam).
2. Restores a Jungle Hawks mount left by a closed or crashed launcher (IL-2 not running).
3. When data\startup.cfg does not have modes = 1, ASKS before changing it (backup first, never silently).
4. Mounts Jungle Hawks through the JSGME routine (jsgme.py: same MODS folder, logs and backups as JSGME) unless it is
   already enabled, starts the game through Steam, waits for IL-2 to close and unloads it again (stock files back from
   MODS\!BACKUP). A JH enabled in JSGME stays enabled; "Keep Jungle Hawks mounted" in the launcher skips the unload.
usage: pythonw jh_launch.pyw [--dry-run]   (--dry-run: do the checks, print the result, start nothing)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jh_installer as J   # noqa: E402

STEAM_RUN = "steam://rungameid/307960"


def jh_enabled(game):
    logs = Path(game) / "MODS" / "!INSTLOGS"
    if not logs.is_dir():
        return []
    return [p.name[:-len(" install.log")] for p in logs.glob("* install.log") if "jungle hawks" in p.name.lower()]


def main():
    dry = "--dry-run" in sys.argv
    game = J.load_json(J.STATE, {}).get("_game") or (str(J.find_game()) if J.find_game() else "")
    if dry:
        g = Path(game) if game else None
        print("game:", game or "not found")
        if g:
            print("JH enabled in JSGME:", jh_enabled(g) or "none", "| would mount:", J.jh_mod_folder(g))
            print("modes:", J.modes_state(g))
        return
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    title = "IL-2: Jungle Hawks"
    if not game or not (Path(game) / "bin" / "game").exists():
        messagebox.showerror(title, "IL-2 Great Battles was not found. Run the Jungle Hawks installer once and pick the "
                                    "IL-2 folder in Settings.")
        return
    try:
        J.recover()
    except Exception as e:  # noqa: BLE001
        messagebox.showerror(title, f"Could not restore the last Jungle Hawks mount:\n{e}")
        return
    if not J.jh_mod_folder(game):
        if not messagebox.askyesno(title, "No Jungle Hawks folder in MODS. Install it with the Jungle Hawks installer."
                                          "\n\nLaunch the game anyway?", icon="warning", default="no"):
            return
        J.start_il2(game)
        return
    m = J.modes_state(game)
    if m != 1:
        if messagebox.askyesno(title, "IL-2's modes setting is off (data\\startup.cfg). Mods need modes = 1.\n\n"
                                      "Set modes = 1 now? A backup of startup.cfg is kept.", icon="question"):
            try:
                J.enable_modes(game)
            except Exception as e:  # noqa: BLE001
                messagebox.showerror(title, f"Could not set modes = 1:\n{e}")
                return
    keep = bool(J.load_json(J.STATE, {}).get("_keep_mounted"))
    J.log(f"launch: JH {J.jh_mod_folder(game)}, modes {J.modes_state(game)}, keep mounted {keep}")
    try:
        J.play(game, unload_after=not keep)          # blocks until IL-2 closes and the stock files are back
    except Exception as e:  # noqa: BLE001
        J.log(f"launch: {e}")
        messagebox.showerror(title, str(e))


if __name__ == "__main__":
    main()
