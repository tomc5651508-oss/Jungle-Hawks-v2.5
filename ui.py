r"""Jungle Hawks installer - the window. Canvas-drawn on the mod's loading-screen art (art\bg_*.png, pre-rendered):
main window (parts + Settings), a separate downloader window that pops out on Install with its own background,
rounded progress bar and live log, and the Cockpit Overlay Builder window. Standard library only (tkinter)."""
import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import jh_installer as J

GREEN, GREEN_HI, INK, DIM, FAINT = "#3fae5a", "#55c871", "#f2f5ef", "#b9c6bc", "#7e8f83"
DARK, PANEL, LINE, WARN = "#0a140f", "#12201a", "#29402f", "#e6b45c"
F_H1 = ("Segoe UI Semibold", 22)
F_H2 = ("Segoe UI Semibold", 13)
F_TXT = ("Segoe UI", 10)
F_SMALL = ("Segoe UI", 9)
F_BIG = ("Segoe UI Light", 34)
F_MONO = ("Consolas", 9)


def rrect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r,
           x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


class Button:
    """canvas pill button with hover"""
    def __init__(self, c, x, y, w, h, text, cmd, primary=True, font=F_H2):
        self.c, self.cmd, self.primary, self.enabled = c, cmd, primary, True
        fill, out = (GREEN, GREEN) if primary else ("", DIM)
        self.bg = rrect(c, x, y, x + w, y + h, h // 2, fill=fill, outline=out, width=1 if not primary else 0)
        self.tx = c.create_text(x + w / 2, y + h / 2, text=text, fill=INK if primary else INK, font=font)
        for item in (self.bg, self.tx):
            c.tag_bind(item, "<Enter>", lambda e: self.hover(True))
            c.tag_bind(item, "<Leave>", lambda e: self.hover(False))
            c.tag_bind(item, "<Button-1>", lambda e: self.enabled and self.cmd())

    def hover(self, on):
        if not self.enabled:
            return
        self.c.config(cursor="hand2" if on else "")
        if self.primary:
            self.c.itemconfig(self.bg, fill=GREEN_HI if on else GREEN)
        else:
            self.c.itemconfig(self.bg, fill="#1c3024" if on else "")

    def enable(self, on):
        self.enabled = on
        self.c.itemconfig(self.bg, fill=(GREEN if on else "#2a3a2f") if self.primary else "")
        self.c.itemconfig(self.tx, fill=INK if on else FAINT)


class Bar:
    """rounded progress bar on a canvas"""
    def __init__(self, c, x, y, w, h=10):
        self.c, self.x, self.y, self.w, self.h = c, x, y, w, h
        rrect(c, x, y, x + w, y + h, h // 2, fill="#25352b", outline="")
        self.fill = rrect(c, x, y, x + h, y + h, h // 2, fill=GREEN, outline="")
        self.set(0)

    def set(self, pct):
        pct = max(0.0, min(100.0, pct))
        x2 = self.x + max(self.h, self.w * pct / 100)
        self.c.delete(self.fill)
        self.fill = rrect(self.c, self.x, self.y, x2, self.y + self.h, self.h // 2, fill=GREEN, outline="")


def art(name):
    p = J.HERE / "art" / name
    return tk.PhotoImage(file=str(p)) if p.exists() else None


def run():
    cfg = J.load_json(J.HERE / "components.json", {})
    comps = cfg.get("components", [])
    tool = cfg.get("cockpit_builder", {})
    saved = J.load_json(J.STATE, {})
    root = tk.Tk()
    root.title("Jungle Hawks")
    root.resizable(False, False)
    W, H = 1000, 640
    c = tk.Canvas(root, width=W, height=H, highlightthickness=0, bg=DARK)
    c.pack()
    imgs = {"main": art("bg_main.png")}
    if imgs["main"]:
        c.create_image(0, 0, image=imgs["main"], anchor="nw")
    game = tk.StringVar(value=str(J.find_game() or saved.get("_game", "")))
    heads, sel = {}, {c_["id"]: c_.get("group") == "base" for c_ in comps}   # both base tracks start selected
    view = {"tab": "install"}

    # header (the logo is part of the art, top-right)
    c.create_text(40, 46, text="Install", anchor="w", font=F_H1, fill=INK, tags=("tab_i",))
    c.create_text(150, 46, text="Settings", anchor="w", font=F_H1, fill=FAINT, tags=("tab_s",))
    under = c.create_line(40, 66, 120, 66, fill=GREEN, width=3)
    c.create_text(40, 92, anchor="w", font=F_TXT, fill=DIM, tags=("sub",),
                  text="The 1942-43 Pacific air war for IL-2 Great Battles")
    for t_, v in (("tab_i", "install"), ("tab_s", "settings")):
        c.tag_bind(t_, "<Button-1>", lambda e, v=v: show(v))
        c.tag_bind(t_, "<Enter>", lambda e: c.config(cursor="hand2"))
        c.tag_bind(t_, "<Leave>", lambda e: c.config(cursor=""))

    layer = {"items": [], "widgets": []}

    def clear():
        for i in layer["items"]:
            c.delete(i)
        for w_ in layer["widgets"]:
            w_.destroy()
        layer["items"], layer["widgets"] = [], []

    def add(i):
        layer["items"].append(i)
        return i

    def show(v):
        view["tab"] = v
        clear()
        c.itemconfig("tab_i", fill=INK if v == "install" else FAINT)
        c.itemconfig("tab_s", fill=INK if v == "settings" else FAINT)
        c.coords(under, *((40, 66, 120, 66) if v == "install" else (150, 66, 262, 66)))
        (draw_install if v == "install" else draw_settings)()

    # ---------------- install view
    def draw_install():
        inst = J.Installer(comps, game.get() or None)
        y = 130
        src_ = J.load_json(J.STATE, {}).get("_source", "wt")
        base_ = [x for x in comps if x.get("group") == "base" and x.get("track", "1946") == src_] or \
            [x for x in comps if x.get("group") == "base"][:1]
        groups = (("Jungle Hawks" + ("  -  WT build (testers)" if src_ == "wt" else "  -  1946 base + builder"), base_),
                  ("Standalone mods for the stock game (not with Jungle Hawks)", [x for x in comps if x.get("group") == "vanilla"]))
        for title, items in groups:
            add(c.create_text(40, y, text=title.upper(), anchor="w", font=("Segoe UI Semibold", 9), fill=GREEN_HI))
            y += 22
            for comp in items:
                st = inst.status(comp, heads.get(comp["id"])) if inst.game else "Pick the IL-2 folder in Settings"
                card = add(rrect(c, 34, y, 600, y + 52, 12, fill=PANEL, outline=LINE, stipple="gray75"))
                dot = add(c.create_oval(50, y + 17, 68, y + 35, outline=GREEN, width=2,
                                        fill=GREEN if sel.get(comp["id"]) else ""))
                add(c.create_text(84, y + 18, text=comp["name"], anchor="w", font=("Segoe UI Semibold", 11), fill=INK))
                col = GREEN_HI if st == "Installed" else (WARN if "Update" in st or "Waiting" in st else DIM)
                add(c.create_text(84, y + 37, text=st, anchor="w", font=F_SMALL, fill=col))
                for it in (card, dot):
                    c.tag_bind(it, "<Button-1>", lambda e, i=comp["id"]: toggle(i))
                y += 60
            y += 10
        b1 = Button(c, 40, H - 92, 220, 50, "Install / Update", start_install)
        b2 = Button(c, 276, H - 86, 170, 38, "Check for updates", lambda: threading.Thread(
            target=check_updates, daemon=True).start(), primary=False, font=F_TXT)
        for b in (b1, b2):
            add(b.bg), add(b.tx)
        add(c.create_text(462, H - 67, anchor="w", font=F_SMALL, fill=FAINT,
                          text="Nothing updates by itself."))

    def toggle(i):
        sel[i] = not sel.get(i)
        show("install")

    # ---------------- settings view
    def draw_settings():
        y = 130
        add(c.create_text(40, y, text="PATHS", anchor="w", font=("Segoe UI Semibold", 9), fill=GREEN_HI))
        y += 26
        add(c.create_text(40, y + 12, text="IL-2 folder", anchor="w", font=F_TXT, fill=DIM))
        e = tk.Entry(root, textvariable=game, bg=PANEL, fg=INK, insertbackground=INK, relief="flat", font=F_TXT,
                     highlightthickness=1, highlightbackground=LINE, highlightcolor=GREEN)
        layer["widgets"].append(e)
        add(c.create_window(160, y, window=e, anchor="nw", width=400, height=26))
        bb = Button(c, 574, y - 2, 96, 30, "Browse", lambda: (game.set(filedialog.askdirectory() or game.get()),
                                                               show("settings")), primary=False, font=F_SMALL)
        add(bb.bg), add(bb.tx)
        g = Path(game.get()) if game.get() else None
        ok = bool(g and (g / "bin" / "game").exists())
        m = J.modes_state(g) if ok else None
        rows = [("JSGME", str(g / "JSGME.exe") if ok else "-", "found" if ok and J.jsgme_present(g) else "missing"),
                ("MODS folder", str(g / "MODS") if ok else "-", "found" if ok and (g / "MODS").exists() else "created on install"),
                ("startup.cfg", str(g / "data" / "startup.cfg") if ok else "-",
                 "modes = 1" if m == 1 else ("modes off" if m == 0 else "start the game once")),
                ("Download cache", str(J.HOME / "repos"), ""), ("Log file", str(J.LOG), "")]
        y += 42
        for label, path, state in rows:
            add(c.create_text(40, y, text=label, anchor="w", font=F_TXT, fill=DIM))
            add(c.create_text(160, y, text=path, anchor="w", font=F_SMALL, fill=INK))
            if state:
                add(c.create_text(820, y, text=state, anchor="w", font=F_SMALL,
                                  fill=GREEN_HI if state in ("found", "modes = 1") else WARN))
            y += 26
        y += 18
        add(c.create_text(40, y, text="GAME SETUP", anchor="w", font=("Segoe UI Semibold", 9), fill=GREEN_HI))
        y += 22
        for x, w, text, fn in ((40, 330, "Enable modes = 1 now (needed for IL-2 mods)", lambda: act(J.enable_modes)),
                               (384, 150, "Install JSGME", lambda: act(J.install_jsgme, cfg.get("jsgme_url", ""),
                                                                      lambda m_, p_=None: None)),
                               (548, 190, "Create MODS folder", lambda: act(J.ensure_mods)),
                               (752, 210, "Desktop shortcut", lambda: threading.Thread(
                                   target=lambda: J.create_shortcut(), daemon=True).start())):
            b = Button(c, x, y, w, 36, text, fn, primary=False, font=F_TXT)
            add(b.bg), add(b.tx)
        y += 48
        add(c.create_text(40, y, anchor="w", font=F_SMALL, fill=FAINT, text="modes = 1 goes into data\\startup.cfg "
                          "([KEY = system]); the first change keeps startup.cfg.bak_jhinstaller. Close the game first."))
        y += 40
        add(c.create_text(40, y, text="BUILD SOURCE", anchor="w", font=("Segoe UI Semibold", 9), fill=GREEN_HI))
        y += 24
        cur = J.load_json(J.STATE, {}).get("_source", "wt")
        for i_, (key, label) in enumerate((("wt", "WT build (testers with GitHub access) - default"),
                                           ("1946", "1946 base + builder (everyone)"))):
            x0 = 40 + i_ * 420
            dot = add(c.create_oval(x0, y - 9, x0 + 18, y + 9, outline=GREEN, width=2, fill=GREEN if cur == key else ""))
            lab = add(c.create_text(x0 + 28, y, anchor="w", font=F_TXT, fill=INK, text=label))
            for it in (dot, lab):
                c.tag_bind(it, "<Button-1>", lambda e, k=key: set_source(k))
        y += 30
        add(c.create_text(40, y, text="GitHub token", anchor="w", font=F_SMALL, fill=DIM))
        tokv = tk.StringVar(value=J.load_json(J.STATE, {}).get("_gh_token", ""))
        te = tk.Entry(root, textvariable=tokv, show="\u2022", bg=PANEL, fg=INK, insertbackground=INK, relief="flat",
                      font=F_SMALL, highlightthickness=1, highlightbackground=LINE, highlightcolor=GREEN)
        layer["widgets"].append(te)
        add(c.create_window(160, y - 12, window=te, anchor="nw", width=300, height=24))
        sv_ = Button(c, 470, y - 14, 70, 28, "Save", lambda: save_token(tokv.get()), primary=False, font=F_SMALL)
        add(sv_.bg), add(sv_.tx)
        add(c.create_text(552, y, anchor="w", font=F_SMALL, fill=FAINT,
                          text="optional - a signed-in GitHub CLI (gh) works too. No access = 1946 is used."))
        y += 34
        add(c.create_text(40, y, text="ACES OF THUNDER", anchor="w", font=("Segoe UI Semibold", 9), fill=GREEN_HI))
        y += 26
        on = bool(J.load_json(J.STATE, {}).get("_aces"))
        box = add(rrect(c, 40, y - 10, 60, y + 10, 5, fill=GREEN if on else "", outline=GREEN, width=2))
        lab = add(c.create_text(72, y, anchor="w", font=F_TXT, fill=INK,
                                text="I own Aces of Thunder / have it installed locally"))
        add(c.create_text(72, y + 22, anchor="w", font=F_SMALL, fill=FAINT,
                          text="Opens the Cockpit Overlay Builder in its own window. It runs on your PC and builds the "
                               "overlay from your own install."))
        for it in (box, lab):
            c.tag_bind(it, "<Button-1>", lambda e: aces_toggle())

    def act(fn, *a):
        if not game_ok():
            return

        def work():
            try:
                fn(game.get(), *a)
            except Exception as e:  # noqa: BLE001
                J.log(f"setup: {e}")
            root.after(0, lambda: show("settings"))
        threading.Thread(target=work, daemon=True).start()

    def set_source(k):
        s = J.load_json(J.STATE, {})
        s["_source"] = k
        J.save_state(s)
        show("settings")

    def save_token(v):
        s = J.load_json(J.STATE, {})
        s["_gh_token"] = v.strip()
        J.save_state(s)
        J.log("GitHub token saved" if v.strip() else "GitHub token cleared")
        show("settings")

    def aces_toggle():
        s = J.load_json(J.STATE, {})
        s["_aces"] = not s.get("_aces")
        J.save_state(s)
        show("settings")
        if s["_aces"]:
            builder_window()

    def game_ok():
        g = game.get()
        if not g or not (Path(g) / "bin" / "game").exists():
            show("settings")
            return False
        return True

    def check_updates():
        for comp in comps:
            if not comp.get("waiting") and comp["id"] in J.load_json(J.STATE, {}):
                heads[comp["id"]] = J.remote_head(comp)
        root.after(0, lambda: view["tab"] == "install" and show("install"))

    # ---------------- downloader (pops out)
    def popout(title, bg_name, parts, on_done=None):
        w = tk.Toplevel(root)
        w.title(title)
        w.resizable(False, False)
        w.transient(root)
        PW, PH = 760, 440
        d = tk.Canvas(w, width=PW, height=PH, highlightthickness=0, bg=DARK)
        d.pack()
        # old-photo background; progress sweeps the colour picture in from the left (the bar is the colour)
        imgs[bg_name] = art(bg_name)
        old = art(bg_name.replace(".png", "_old.png"))
        if imgs[bg_name]:
            d.create_image(0, 0, image=imgs[bg_name], anchor="nw")
        sweep = {"img": None, "item": None, "x": -1, "old": old}
        edge = d.create_line(0, 0, 0, PH, fill="#fff3d6", width=2, state="hidden")

        def sweep_to(pct_):
            x = int(PW * max(0.0, min(100.0, pct_)) / 100)
            if not old or x == sweep["x"]:
                return
            sweep["x"] = x
            if sweep["item"]:
                d.delete(sweep["item"])
                sweep["item"] = None
            if x < PW:
                piece = tk.PhotoImage(width=PW - x, height=PH)
                piece.tk.call(piece, "copy", old, "-from", x, 0, PW, PH, "-to", 0, 0)
                sweep["img"] = piece
                sweep["item"] = d.create_image(x, 0, image=piece, anchor="nw")
                d.tag_lower(sweep["item"])
                d.tag_lower(sweep["item"])
                d.tag_raise(sweep["item"], "bgimg") if d.find_withtag("bgimg") else None
            d.coords(edge, x, 0, x, PH)
            d.itemconfig(edge, state="normal" if 0 < x < PW else "hidden")
        if imgs[bg_name]:
            d.itemconfig(d.find_all()[0], tags=("bgimg",))
        sweep_to(0)
        d.create_text(40, 168, text=title, anchor="w", font=F_H1, fill=INK, width=PW - 80)
        part = d.create_text(40, 250, text="", anchor="w", font=F_H2, fill=INK)
        pct = d.create_text(PW - 40, 262, text="0%", anchor="e", font=F_BIG, fill=INK)
        rrect(d, 40, 296, PW - 40, 306, 5, fill="", outline="#fff3d6", width=1)

        class _Bar:
            def set(self, v):
                sweep_to(v)
        bar = _Bar()
        msg = d.create_text(40, 322, text="Starting...", anchor="w", font=F_SMALL, fill=DIM, width=PW - 80)
        logl = d.create_text(40, 346, text="", anchor="nw", font=F_MONO, fill=FAINT, width=PW - 80)
        lines = []
        close = Button(d, PW - 170, PH - 58, 130, 38, "Close", w.destroy, primary=False, font=F_TXT)
        close.enable(False)
        state = {"done": 0, "n": len(parts)}

        def ui(fn):
            w.after(0, fn)

        def on_log(line):
            lines.append(line[9:] if len(line) > 9 else line)
            ui(lambda: d.itemconfig(logl, text="\n".join(lines[-5:])))

        def prog(m, p=None):
            def f():
                d.itemconfig(msg, text=m)
                if p is not None:
                    tot = (state["done"] * 100 + p) / max(1, state["n"])
                    bar.set(tot)
                    d.itemconfig(pct, text=f"{tot:.0f}%")
            ui(f)
        J._log_sink.append(on_log)

        def finish(text):
            J._log_sink.remove(on_log)
            ui(lambda: (d.itemconfig(msg, text=text), close.enable(True)))
            if on_done:
                root.after(0, on_done)
        return w, d, part, prog, state, finish

    def start_install():
        if not game_ok():
            return
        inst = J.Installer(comps, game.get())
        src_ = J.load_json(J.STATE, {}).get("_source", "wt")
        chosen = [x for x in comps if sel.get(x["id"]) and (x.get("group") != "base" or x.get("track", "1946") == src_)]
        todo = [x for x in chosen if not x.get("waiting")]
        for x in chosen:
            if x.get("waiting"):
                J.log(f"{x['name']}: not released yet - skipped")
        if not todo:
            J.log("nothing to install: select a released part")
            show("install")
            return
        s = J.load_json(J.STATE, {})
        s["_game"] = game.get()
        J.save_state(s)
        w, d, part, prog, state, finish = popout("Downloading", "bg_download.png", todo, lambda: show("install"))

        def work():
            errs = []
            g = game.get()
            J.ensure_mods(g)
            if not J.jsgme_present(g):
                try:
                    J.install_jsgme(g, cfg.get("jsgme_url", ""), prog)
                except Exception as e:  # noqa: BLE001
                    J.log(f"JSGME: {e}")
            for comp in todo:
                w.after(0, lambda n=comp["name"]: d.itemconfig(part, text=n))
                try:
                    try:
                        J.Installer(comps, g).install(comp, prog)
                    except J.NoAccess as e:
                        alt = next((x for x in comps if x.get("group") == "base" and x.get("track") == "1946"), None)
                        if comp.get("track") != "wt" or not alt:
                            raise
                        J.log(f"WT build: {e}. No access to the WT test build with this GitHub sign-in - installing "
                              "the 1946 base instead. Tick Aces of Thunder in Settings to build the WT parts on this PC.")
                        w.after(0, lambda n=alt["name"]: d.itemconfig(part, text=n))
                        comp = alt
                        J.Installer(comps, g).install(comp, prog)
                    heads[comp["id"]] = J.load_json(J.STATE, {})[comp["id"]]["commit"]
                except Exception as e:  # noqa: BLE001
                    errs.append(comp["name"])
                    J.log(f"FAILED {comp['name']}: {e}")
                state["done"] += 1
            finish("Done. Open JSGME in the IL-2 folder and enable Jungle Hawks." if not errs
                   else "Problems with: " + ", ".join(errs) + " - see the log file in Settings.")
        threading.Thread(target=work, daemon=True).start()

    # ---------------- Cockpit Overlay Builder (pops out)
    def builder_window():
        if not game_ok():
            return
        tid = tool.get("id", "builder")
        w, d, part, prog, state, finish = popout(tool.get("name", "Cockpit Overlay Builder"), "bg_builder.png", [tool])
        d.itemconfig(part, text=tool.get("about", ""), font=F_TXT, width=680)
        d.coords(part, 40, 212)
        prog("Ready.", 0)

        def start_tool():
            p = Path(J.load_json(J.STATE, {}).get(tid, {}).get("path", ""))
            cmd = [x.replace("{repo}", str(p)).replace("{game}", game.get()) for x in tool.get("start", [])]
            if cmd and p.exists():
                J.log("starting the Cockpit Overlay Builder")
                subprocess.Popen(cmd, cwd=p)

        go = Button(d, 300, 440 - 58, 160, 38, "Start the tool", start_tool, primary=True, font=F_TXT)
        go.enable(tid in J.load_json(J.STATE, {}))

        def dl():
            def work():
                try:
                    comp = dict(tool, id=tid)
                    J.Installer([comp], game.get()).install(comp, prog)
                    w.after(0, lambda: go.enable(True))
                except Exception as e:  # noqa: BLE001
                    J.log(f"FAILED: {e}")
            threading.Thread(target=work, daemon=True).start()
        Button(d, 40, 440 - 58, 240, 38, "Download / update the tool", dl, primary=True, font=F_TXT)

    # support link, bottom right on every view
    sup = c.create_text(W - 30, H - 26, text="☕  Support Pingu - buymeacoffee.com/pingu565", anchor="e",
                        font=("Segoe UI Semibold", 10), fill="#f0c674")
    c.tag_bind(sup, "<Button-1>", lambda e: __import__("webbrowser").open("https://buymeacoffee.com/pingu565"))
    c.tag_bind(sup, "<Enter>", lambda e: (c.config(cursor="hand2"), c.itemconfig(sup, fill="#ffe09a")))
    c.tag_bind(sup, "<Leave>", lambda e: (c.config(cursor=""), c.itemconfig(sup, fill="#f0c674")))
    show("install")
    threading.Thread(target=check_updates, daemon=True).start()
    J.log(f"JH Installer {J.VERSION} started")
    if "--shot" in sys.argv:
        shots(root, c, show, popout, builder_window, Path(sys.argv[sys.argv.index("--shot") + 1]))
    root.mainloop()


def shots(root, c, show, popout, builder_window, out):
    """docs: render the views to PNG (main, settings, downloader mid-run, builder) and close"""
    from PIL import ImageGrab

    def grab(win, name):
        win.attributes("-topmost", True)
        win.lift()
        win.update()
        import time
        time.sleep(0.4)
        x, y = win.winfo_rootx(), win.winfo_rooty()
        ImageGrab.grab((x, y, x + win.winfo_width(), y + win.winfo_height())).save(out / name)

    def demo_dl():
        w, d, part, prog, state, finish = popout("Downloading", "bg_download.png", [1])
        d.itemconfig(part, text="Jungle Hawks 2.5")
        for ln in ("Jungle Hawks 2.5: cloning (release)", "Jungle Hawks 2.5: receiving", "Jungle Hawks 2.5: resolving"):
            J.log(ln)
        prog("Jungle Hawks 2.5: Receiving objects:  64% (1532/2391), 1.21 GiB | 18.4 MiB/s", 62)
        root.after(900, lambda: grab(w, "ui_downloader.png"))
        root.after(1300, lambda: (finish("demo"), w.destroy()))
    root.after(1200, lambda: grab(root, "ui_install.png"))
    root.after(1700, lambda: show("settings"))
    root.after(2300, lambda: grab(root, "ui_settings.png"))
    root.after(2600, lambda: show("install"))
    root.after(2800, demo_dl)
    root.after(4600, builder_window)
    root.after(5600, lambda: grab(root.winfo_children()[-1], "ui_builder.png"))
    root.after(6200, root.destroy)
