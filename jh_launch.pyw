r"""IL-2: Jungle Hawks launcher (the Desktop shortcut runs this).

1. Finds the IL-2 folder (installer state, else Steam).
2. Warns when no Jungle Hawks folder is enabled in JSGME (MODS\!INSTLOGS\<name> install.log): Launch anyway / Cancel.
3. When data\startup.cfg does not have modes = 1, ASKS before changing it (backup first, never silently).
4. Starts the game through Steam (steam://rungameid/307960).
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
            print("JH enabled in JSGME:", jh_enabled(g) or "none")
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
    on = jh_enabled(game)
    if not on:
        if not messagebox.askyesno(title, "Jungle Hawks is not enabled in JSGME.\n\nOpen JSGME (in the IL-2 folder), "
                                          "enable Jungle Hawks, then start again.\n\nLaunch the game anyway?",
                                   icon="warning", default="no"):
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
    J.log(f"launch: JH enabled {on or 'none'}, modes {J.modes_state(game)}")
    os.startfile(STEAM_RUN)


if __name__ == "__main__":
    main()
