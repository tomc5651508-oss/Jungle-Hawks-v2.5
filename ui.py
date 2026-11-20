r"""Jungle Hawks launcher - the window. Original launcher layout (folder tabs top-left, controls on the left, picture on
the right) re-skinned with Pingu's JH PWCG campaign-pack images (art\desk_*.png, made by make_desk.py from
D:\PWCGCampaign\BoSData\Images: TableTop desk, paperFull sheet + tabs, map card / writing pad / certificate / profile
from CampaignGenFullScreen, TranslucentButton) with modern JH screenshots as photos. PWCG font = bold serif.
The downloader and the Cockpit Overlay Builder pop out in their own windows. Standard library only (tkinter)."""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox

import jh_installer as J

GREEN, GREEN_HI, INK, DIM, FAINT = "#3fae5a", "#55c871", "#f2f5ef", "#b9c6bc", "#7e8f83"
DARK, PANEL, LINE, WARN = "#0a140f", "#12201a", "#29402f", "#e6b45c"
PEN, PEN_RED, PEN_GREEN, PAPER, CHALK = "#24180c", "#8a1c10", "#2f5a22", "#eadfc4", "#f3ece0"
PEN_ORANGE = "#c0600c"          # "Ready" while an update for the installed Jungle Hawks is waiting
F_H1 = ("Segoe UI Semibold", 22)
F_H2 = ("Segoe UI Semibold", 13)
F_TXT = ("Segoe UI", 10)
F_SMALL = ("Segoe UI", 9)
F_BIG = ("Segoe UI Light", 34)
F_MONO = ("Consolas", 9)
F_HAND = ("Segoe Print", 10, "bold")      # the hand-written journal lines
F_HAND_S = ("Segoe Print", 8)
F_TYPE = ("Courier New", 10, "bold")      # typewritten list lines
F_TYPE_S = ("Courier New", 8)
F_BTN = ("Georgia", 12, "bold")
SERIF = "Georgia"           # PWCG GUI font = bold Serif


def rrect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r,
           x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


class Button:
    """canvas pill button with hover (pop-out windows)"""
    def __init__(self, c, x, y, w, h, text, cmd, primary=True, font=F_H2):
        self.c, self.cmd, self.primary, self.enabled = c, cmd, primary, True
        fill, out = (GREEN, GREEN) if primary else ("", DIM)
        self.bg = rrect(c, x, y, x + w, y + h, h // 2, fill=fill, outline=out, width=1 if not primary else 0)
        self.tx = c.create_text(x + w / 2, y + h / 2, text=text, fill=INK, font=font)
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


class PwcgButton:
    """the PWCG campaign-pack button (TranslucentButton.png) with hand-written label"""
    def __init__(self, c, img, x, y, text, cmd, ink=PEN, font=F_BTN):
        self.c, self.cmd, self.ink, self.enabled = c, cmd, ink, True
        self.bg = c.create_image(x, y, image=img, anchor="nw")
        self.tx = c.create_text(x + img.width() / 2, y + img.height() / 2, text=text, fill=ink, font=font)
        for item in (self.bg, self.tx):
            c.tag_bind(item, "<Enter>", lambda e: self.enabled and (c.config(cursor="hand2"),
                                                                     c.itemconfig(self.tx, fill=PEN_RED)))
            c.tag_bind(item, "<Leave>", lambda e: (c.config(cursor=""), c.itemconfig(self.tx, fill=self._ink())))
            c.tag_bind(item, "<Button-1>", lambda e: self.enabled and self.cmd())

    def _ink(self):
        return self.ink if self.enabled else "#8c8070"

    def enable(self, on):
        self.enabled = on
        self.c.itemconfig(self.tx, fill=self._ink())

    def items(self):
        return self.bg, self.tx


class PlateButton:
    """the main actions on the black plate of the JH menu logo (copper rim), chalk-white lettering, glow on hover"""
    def __init__(self, c, img, img_hover, x, y, text, cmd, font):
        self.c, self.cmd, self.enabled, self.x, self.y = c, cmd, True, x, y
        self.img, self.img_h = img, img_hover
        self.bg = c.create_image(x, y, image=img, anchor="nw")
        self.tx = c.create_text(x + img.width() / 2, y + img.height() / 2, text=text, fill=CHALK, font=font)
        for item in (self.bg, self.tx):
            c.tag_bind(item, "<Enter>", lambda e: self.hover(True))
            c.tag_bind(item, "<Leave>", lambda e: self.hover(False))
            c.tag_bind(item, "<Button-1>", lambda e: self.enabled and self.cmd())

    def hover(self, on):
        if not self.enabled:
            return
        self.c.config(cursor="hand2" if on else "")
        self.c.itemconfig(self.bg, image=self.img_h if on else self.img)
        self.c.coords(self.bg, self.x - (8 if on else 0), self.y - (8 if on else 0))
        self.c.itemconfig(self.tx, fill="#ffb060" if on else CHALK)

    def enable(self, on):
        self.enabled = on
        self.c.itemconfig(self.tx, fill=CHALK if on else "#6e655a")

    def items(self):
        return self.bg, self.tx


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


def borderless(root):
    """no Windows title bar; keep the taskbar button (WS_EX_APPWINDOW) so the window can be minimised and found"""
    root.overrideredirect(True)
    if os.name != "nt":
        return
    import ctypes
    root.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
    GWL_EXSTYLE, WS_EX_APPWINDOW, WS_EX_TOOLWINDOW = -20, 0x40000, 0x80
    st = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (st & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW)
    root.withdraw()
    root.after(10, root.deiconify)


def minimise(root):
    if os.name == "nt":
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.user32.GetParent(root.winfo_id()), 6)   # SW_MINIMIZE
    else:
        root.iconify()


class Music:
    """IL-2 1946 IJN menu theme (art\\menu_ijn_1946.wav, MP3-in-WAV) on a loop through Windows MCI; no extra packages"""
    def __init__(self, path):
        self.path, self.open, self.playing = Path(path), False, False

    def _mci(self, cmd):
        if os.name != "nt":
            return 1
        import ctypes
        return ctypes.windll.winmm.mciSendStringW(cmd, None, 0, 0)

    def play(self):
        if self.playing or not self.path.exists():
            return
        if not self.open:
            self.open = self._mci(f'open "{self.path}" type mpegvideo alias jhmusic') == 0
        if self.open and self._mci("play jhmusic from 0 repeat") == 0:
            self.playing = True

    def stop(self):
        if self.open:
            self._mci("stop jhmusic")
        self.playing = False

    def close(self):
        if self.open:
            self._mci("close jhmusic")
        self.open = self.playing = False


# Aircraft Information: the flight-model handbooks (docs\\fm) - each type's two-page technical note, and the stock
# aircraft it flies in place of (the build's planes.tab.eng, WT 27.3)
HANDBOOKS = (
    ("Japanese aircraft", "RAAF Handbook of Japanese Aircraft Performance Charts, 1943",
     "RAAF_Handbook_Japanese_Aircraft_Performance.pdf",
     (("A6M2 Model 21 Zero", 3, "LaGG-3 ser.29"), ("A6M3 Model 32 Zero", 5, "Fw 190 A-5"),
      ("A6M5 Model 52 Zero", 7, "Yak-1 ser.69"), ("Ki-43-II Hayabusa", 9, "Bf 109 F-2"), ("Ki-61-I Hien", 11, "Bf 109 F-4"),
      ("Ki-45 KAI Toryu", 13, "Bf 110 E-2"), ("Ki-46-III", 15, "Bf 110 G-2"), ("D3A1 Val", 17, "Ju 87 D-3"),
      ("G4M1 Betty", 19, "Ju 88 A-4"), ("Ki-21-IIb Sally", 21, "Pe-2 ser.87"), ("L2D2 Tabby", 23, "Ju 52/3m"))),
    ("Allied aircraft", "IJN Handbook of Allied Aircraft Performance Charts, 1943",
     "IJN_Handbook_Allied_Aircraft_Performance.pdf",
     (("F4F-4 Wildcat", 3, "P-51B-5"), ("F4U-1D Corsair", 5, "P-47D-22"), ("SBD-3 Dauntless", 7, "IL-2 mod.1942"),
      ("TBF-1 Avenger", 9, "IL-2 mod.1944"), ("B-17E Flying Fortress", 11, "Pe-2 ser.35"),
      ("Beaufighter TF.X", 13, "Mosquito FB Mk.VI"), ("Beaufort Mk.I", 15, "He 111 H-6"))),
)


# profile pages: picture = the type's in-mod preview profile (art\\planes, from the 1946 build's preview2.png), stats =
# the historical targets the flight model is fitted to (handbook notes). key: (picture, role, code name, top speed,
# climb, power, loaded weight, wing area, wing loading, sustained turn)
PROFILES = {
    "A6M2 Model 21 Zero": ("a6m2", "Carrier fighter, Imperial Japanese Navy", "Zeke", "533 km/h at 4,550 m", "15.0 m/s",
                           "940 hp Sakae 12", "2,410 kg", "22.44 m\u00b2", "107 kg/m\u00b2", "14.6 s"),
    "A6M3 Model 32 Zero": ("a6m3", "Carrier fighter, Imperial Japanese Navy", "Hamp", "544 km/h at 6,000 m", "15.2 m/s",
                           "1,130 hp Sakae 21", "2,544 kg", "21.53 m\u00b2", "118 kg/m\u00b2", "15.6 s"),
    "A6M5 Model 52 Zero": ("a6m5", "Carrier fighter, Imperial Japanese Navy", "Zeke 52", "565 km/h at 6,000 m",
                           "15.7 m/s", "1,130 hp Sakae 21", "2,733 kg", "21.30 m\u00b2", "128 kg/m\u00b2", "15.8 s"),
    "Ki-43-II Hayabusa": ("ki43", "Fighter, Imperial Japanese Army", "Oscar", "530 km/h at 4,000 m", "17.9 m/s",
                          "1,150 hp Ha-115", "2,590 kg", "21.40 m\u00b2", "121 kg/m\u00b2", "16.4 s"),
    "Ki-61-I Hien": ("ki61", "Fighter, Imperial Japanese Army", "Tony", "590 km/h at 4,860 m", "18.9 m/s",
                     "1,175 hp Ha-40", "3,470 kg", "20.00 m\u00b2", "174 kg/m\u00b2", "21.8 s"),
    "Ki-45 KAI Toryu": ("ki45", "Twin-engine heavy fighter, Imperial Japanese Army", "Nick", "540 km/h at 6,000 m",
                        "15.0 m/s", "2 x 1,080 hp Ha-102", "5,500 kg", "32.00 m\u00b2", "172 kg/m\u00b2", "24.2 s"),
    "Ki-46-III": ("ki46", "Reconnaissance, Imperial Japanese Army", "Dinah", "630 km/h at 6,000 m",
                  "8,000 m in 20.2 min", "2 x 1,500 hp Ha-112-II", "5,722 kg", "32.00 m\u00b2", "179 kg/m\u00b2", "18.8 s"),
    "D3A1 Val": ("d3a1", "Carrier dive bomber, Imperial Japanese Navy", "Val", "387 km/h at 2,350 m", "9.7 m/s",
                 "1,000 hp Kinsei 43", "3,650 kg", "34.90 m\u00b2", "105 kg/m\u00b2", "15.8 s"),
    "G4M1 Betty": ("g4m1", "Land-based bomber, Imperial Japanese Navy", "Betty", "428 km/h at 4,200 m", "7.9 m/s",
                   "2 x 1,530 hp Kasei 11", "9,500 kg", "78.13 m\u00b2", "122 kg/m\u00b2", "16.2 s"),
    "Ki-21-IIb Sally": ("ki21", "Heavy bomber, Imperial Japanese Army", "Sally", "486 km/h at 4,720 m", "9.6 m/s",
                        "2 x 1,500 hp Ha-101", "9,710 kg", "69.60 m\u00b2", "140 kg/m\u00b2", "23.6 s"),
    "L2D2 Tabby": ("l2d2", "Transport, Imperial Japanese Navy", "Tabby", "360 km/h at 3,000 m", "6.2 m/s",
                   "2 x 1,000 hp Kinsei 43", "10,900 kg", "91.70 m\u00b2", "119 kg/m\u00b2", "25.6 s"),
    "F4F-4 Wildcat": ("f4f4", "Carrier fighter, US Navy and Marines", "", "512 km/h at 5,900 m", "9.9 m/s",
                      "1,200 hp R-1830", "3,607 kg", "24.15 m\u00b2", "149 kg/m\u00b2", "16.8 s"),
    "F4U-1D Corsair": ("f4u1d", "Fighter-bomber, US Navy and Marines", "", "684 km/h at 6,100 m", "15.8 m/s",
                       "2,250 hp R-2800", "5,461 kg", "29.17 m\u00b2", "187 kg/m\u00b2", "23.8 s"),
    "SBD-3 Dauntless": ("sbd3", "Carrier dive bomber, US Navy", "", "402 km/h at 4,875 m", "6.0 m/s",
                        "1,000 hp R-1820", "4,318 kg", "30.19 m\u00b2", "143 kg/m\u00b2", "29.3 s"),
    "TBF-1 Avenger": ("tbf1", "Carrier torpedo bomber, US Navy", "", "436 km/h at 3,660 m", "7.3 m/s",
                      "1,700 hp R-2600", "7,215 kg", "45.52 m\u00b2", "159 kg/m\u00b2", "28.5 s"),
    "B-17E Flying Fortress": ("b17e", "Heavy bomber, US Army Air Forces", "", "510 km/h at 7,620 m", "4.5 m/s",
                              "4 x 1,200 hp R-1820", "18,262 kg", "131.92 m\u00b2", "138 kg/m\u00b2", "23.8 s"),
    "Beaufighter TF.X": ("beaufighter", "Strike fighter, RAAF", "", "515 km/h at 3,050 m", "8.1 m/s",
                         "2 x 1,770 hp Hercules", "11,431 kg", "46.73 m\u00b2", "245 kg/m\u00b2", "31.1 s"),
    "Beaufort Mk.I": ("beaufort", "Torpedo bomber, RAAF", "", "426 km/h at 1,830 m", "6.1 m/s",
                      "2 x 1,130 hp Taurus", "9,629 kg", "46.73 m\u00b2", "206 kg/m\u00b2", "28.4 s"),
}


FM_PAGES = {"RAAF_Handbook_Japanese_Aircraft_Performance.pdf": ("raaf", 24),
            "IJN_Handbook_Allied_Aircraft_Performance.pdf": ("ijn", 16)}    # art\\fm\\<tag>_NN.png, pre-rendered


def open_pdf(name, page=1):
    """open a handbook at a page: Edge / Chrome take file:///...#page=N; else the default PDF viewer at page 1"""
    pdf = J.HERE / "docs" / "fm" / name
    if not pdf.exists():
        J.log(f"aircraft info: {pdf} missing")
        return
    url = pdf.as_uri() + f"#page={page}"
    for exe in (r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
                r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
                r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
                r"%LocalAppData%\Google\Chrome\Application\chrome.exe"):
        e = Path(os.path.expandvars(exe))
        if e.exists():
            subprocess.Popen([str(e), url])
            return
    os.startfile(str(pdf))


def short(p, n=44):
    p = str(p)
    return p if len(p) <= n else "..." + p[-(n - 3):]


def run():
    cfg = J.load_json(J.HERE / "components.json", {})
    comps = cfg.get("components", [])
    tool = cfg.get("cockpit_builder", {})
    saved = J.load_json(J.STATE, {})
    root = tk.Tk()
    root.title("Pingu's Jungle Hawks v2.5")
    root.resizable(False, False)
    W, H = 1000, 640
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    if "--shot" in sys.argv and J.il2_running():
        sys.exit("IL-2 is running - screenshots wait until the game is closed (the window would open over it)")
    root.geometry(f"{W}x{H}+{(sw - W) // 2}+{max(0, (sh - H) // 2 - 30)}")
    ico = J.HERE / "art" / "jh_launch.ico"
    if ico.exists():
        try:
            root.iconbitmap(str(ico))
        except tk.TclError:
            pass
    c = tk.Canvas(root, width=W, height=H, highlightthickness=0, bg="#2a1a10")
    c.pack()
    imgs = {k: art(f"desk_{k}.png") for k in ("play", "install", "settings", "aircraft", "a3")}
    imgs["plugins"] = art("desk_plugins.png") or imgs["settings"]
    imgs.update({k: art(f"{k}.png") for k in ("b_big", "b_mid", "b_small", "b_tiny", "b_foot", "plate_big", "plate_big_hover", "poster_support",
                                                "poster_support_hover")})
    music = Music(J.HERE / "art" / "menu_ijn_1946.wav")
    if not saved.get("_muted") and "--shot" not in sys.argv:
        music.play()
    bg = c.create_image(0, 0, image=imgs["play"], anchor="nw")
    if "--framed" not in sys.argv:
        borderless(root)
    game = tk.StringVar(value=str(J.find_game() or saved.get("_game", "")))
    # Tk is only touched from the main thread: worker threads read the game folder from a plain copy and hand UI work
    # to later(), which the main loop runs (a Tk call from a worker thread corrupts Tcl memory: "Tcl_Panic" crash)
    _game_v = {"v": game.get()}
    game.trace_add("write", lambda *a: _game_v.__setitem__("v", game.get()))
    _todo = queue.Queue()

    def gval():
        return _game_v["v"]

    def later(fn):
        _todo.put(fn)

    def pump():
        try:
            while True:
                fn = _todo.get_nowait()
                try:
                    fn()
                except tk.TclError as e:          # its window was closed meanwhile
                    J.log(f"ui: {str(e)[:120]}")
        except queue.Empty:
            pass
        root.after(50, pump)
    root.after(50, pump)
    heads, sel = {}, {c_["id"]: True for c_ in comps if c_.get("group") == "base"}   # both base tracks start selected
    view = {"tab": "play"}
    playing = {"on": False, "quit": False}

    # folder tabs on the top edge of the paper sheet
    TABS = (("play", "Play"), ("install", "Install"), ("settings", "Settings"), ("plugins", "Plugins"))
    tabx, x_ = {}, 34
    for key, label in TABS:
        imgs[f"t_{key}_on"] = art(f"ftab_{key}_on.png") or art("ftab_settings_on.png")      # Plugins borrows the
        imgs[f"t_{key}_off"] = art(f"ftab_{key}_off.png") or art("ftab_settings_off.png")   # blank Settings tab
        w_ = imgs[f"t_{key}_on"].width()
        c.create_image(x_, 24, image=imgs[f"t_{key}_off"], anchor="nw", tags=(f"tab_{key}", f"tabimg_{key}"))
        c.create_text(x_ + w_ / 2, 44, text=label, font=(SERIF, 14, "bold"), fill=PEN,
                      tags=(f"tab_{key}", f"tablab_{key}"))
        c.tag_bind(f"tab_{key}", "<Button-1>", lambda e, v=key: show(v))
        c.tag_bind(f"tab_{key}", "<Enter>", lambda e: c.config(cursor="hand2"))
        c.tag_bind(f"tab_{key}", "<Leave>", lambda e: c.config(cursor=""))
        tabx[key] = x_
        x_ += w_ + 4
    # Aircraft Info: the leather binder's tab, hanging from the bottom edge of the window, centred (Pingu 19 Nov:
    # at the top it covered the Jungle Hawks title art)
    imgs["bt_on"] = art("btab_on_bottom.png") or art("btab_on.png")
    imgs["bt_off"] = art("btab_off_bottom.png") or art("btab_off.png")
    BTW, BTH = imgs["bt_off"].width(), imgs["bt_off"].height()
    BTX, BTY = (W - BTW) // 2, H - BTH
    c.create_image(BTX, BTY + 4, image=imgs["bt_off"], anchor="nw", tags=("tab_aircraft", "tabimg_aircraft"))
    c.create_text(BTX + BTW / 2, BTY + BTH / 2 + 2, text="Aircraft Info", font=(SERIF, 14, "bold"), fill=CHALK,
                  tags=("tab_aircraft", "tablab_aircraft"))
    c.tag_bind("tab_aircraft", "<Button-1>", lambda e: show("aircraft"))
    c.tag_bind("tab_aircraft", "<Enter>", lambda e: c.config(cursor="hand2"))
    c.tag_bind("tab_aircraft", "<Leave>", lambda e: c.config(cursor=""))
    # window buttons (no Windows title bar): minimise, close
    for k, (gx, glyph, fn) in enumerate(((W - 58, "\u2013", lambda: minimise(root)), (W - 22, "\u2715", lambda: close()))):
        c.create_rectangle(gx - 16, 0, gx + 16, 28, fill="", outline="", tags=(f"wb{k}",))
        c.create_text(gx, 14, text=glyph, font=("Segoe UI", 13, "bold"), fill=CHALK, tags=(f"wb{k}", f"wbt{k}"))
        c.tag_bind(f"wb{k}", "<Button-1>", lambda e, f=fn: f())
        c.tag_bind(f"wb{k}", "<Enter>", lambda e, k=k: (c.config(cursor="hand2"),
                                                       c.itemconfig(f"wbt{k}", fill="#ff5a3a" if k else "#ffffff")))
        c.tag_bind(f"wb{k}", "<Leave>", lambda e, k=k: (c.config(cursor=""), c.itemconfig(f"wbt{k}", fill=CHALK)))
    # drag the window by the top strip (anything up there that is not a tab or a window button)
    drag = {"x": 0, "y": 0, "on": False}

    def drag_start(e):
        hit = c.find_overlapping(e.x, e.y, e.x, e.y)
        tagged = {tg for i in hit for tg in c.gettags(i)}
        drag["on"] = e.y < 60 and not any(tg.startswith(("tab_", "wb", "ui")) for tg in tagged)
        drag["x"], drag["y"] = e.x_root - root.winfo_x(), e.y_root - root.winfo_y()

    def drag_move(e):
        if drag["on"]:
            root.geometry(f"+{e.x_root - drag['x']}+{e.y_root - drag['y']}")
    c.bind("<ButtonPress-1>", drag_start, add="+")
    c.bind("<B1-Motion>", drag_move, add="+")

    def close():
        if playing["on"]:          # IL-2 is running with a launcher-mounted JH: restore first, then quit
            playing["quit"] = True
            minimise(root)
            return
        music.close()
        root.destroy()

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

    def btn(img, x, y, text, cmd, size=13, ink=PEN):
        b = PwcgButton(c, imgs[img], x, y, text, cmd, ink, (SERIF, size, "bold"))
        for i in b.items():
            add(i)
        return b

    def plate_btn(x, y, text, cmd):
        b = PlateButton(c, imgs["plate_big"], imgs["plate_big_hover"], x, y, text, cmd, (SERIF, 17, "bold"))
        for i in b.items():
            add(i)
        return b

    def tick(x, y, on, text, cmd, ink=PEN, font=(SERIF, 12, "bold")):
        box = add(c.create_rectangle(x, y - 8, x + 16, y + 8, outline=ink, width=2))
        mark = add(c.create_text(x + 8, y - 1, text="\u2714" if on else "", font=("Segoe UI Symbol", 13, "bold"),
                                 fill=PEN_RED))
        lab = add(c.create_text(x + 26, y, anchor="w", font=font, fill=ink, text=text))
        for it in (box, mark, lab):
            c.tag_bind(it, "<Button-1>", lambda e: cmd())
            c.tag_bind(it, "<Enter>", lambda e: c.config(cursor="hand2"))
            c.tag_bind(it, "<Leave>", lambda e: c.config(cursor=""))

    def show(v):
        if v != view["tab"]:
            view.pop("profile", None)
            view.pop("viewer", None)
        view["tab"] = v
        clear()
        c.itemconfig(bg, image=imgs[("a3" if view.get("profile") and not view.get("viewer") else "aircraft")
                                    if v == "aircraft" else v])
        for key, _ in TABS:
            on = key == v
            c.itemconfig(f"tabimg_{key}", image=imgs[f"t_{key}_{'on' if on else 'off'}"])
            c.itemconfig(f"tablab_{key}", fill=PEN if on else "#3a2a18")
            c.coords(f"tabimg_{key}", tabx[key], 22 if on else 26)
        onb = v == "aircraft"
        c.itemconfig("tabimg_aircraft", image=imgs["bt_on" if onb else "bt_off"])
        c.itemconfig("tablab_aircraft", fill="#ffffff" if onb else "#e3cdb8")
        c.coords("tabimg_aircraft", BTX, BTY if onb else BTY + 4)
        c.tag_raise("tab_aircraft")
        {"play": draw_play, "install": draw_install, "settings": draw_settings, "plugins": draw_plugins,
         "aircraft": draw_aircraft}[v]()
        warbonds()

    def warbonds():
        """bottom right on every tab: the support poster (the whole poster is the link, grows a little on hover) and,
        under it, MUTE AUDIO for the 1946 IJN menu theme"""
        cx, by = W - 108, H - 58                 # poster centre x, poster bottom y
        if view.get("poster_small"):             # minimised: just a SUPPORT PINGU button (+ opens the poster again)
            sp = btn("b_small", W - 208, H - 88, "SUPPORT PINGU", open_support, size=12)
            c.itemconfig(sp.tx, fill=PEN_RED)
            bx = add(c.create_rectangle(W - 230, H - 79, W - 212, H - 61, fill="#1a120a", outline=CHALK))
            pl = add(c.create_text(W - 221, H - 70, text="+", font=("Segoe UI", 11, "bold"), fill=CHALK))
            for it in (bx, pl):
                c.tag_bind(it, "<Button-1>", lambda e: (view.__setitem__("poster_small", False), show(view["tab"])))
                c.tag_bind(it, "<Enter>", lambda e: c.config(cursor="hand2"))
                c.tag_bind(it, "<Leave>", lambda e: c.config(cursor=""))
        else:
            po = add(c.create_image(cx, by, image=imgs["poster_support"], anchor="s", tags=("ui_poster",)))
            c.tag_bind(po, "<Enter>", lambda e: (c.config(cursor="hand2"),
                                                 c.itemconfig(po, image=imgs["poster_support_hover"]),
                                                 c.coords(po, cx, by + 6)))
            c.tag_bind(po, "<Leave>", lambda e: (c.config(cursor=""), c.itemconfig(po, image=imgs["poster_support"]),
                                                 c.coords(po, cx, by)))
            c.tag_bind(po, "<Button-1>", lambda e: open_support())
            top = by - imgs["poster_support"].height()           # small minimise box on the poster's top-right corner
            mx = cx + imgs["poster_support"].width() // 2 - 12
            box = add(c.create_rectangle(mx - 9, top + 3, mx + 9, top + 21, fill="#1a120a", outline=CHALK,
                                         tags=("ui_pmin",)))
            mn = add(c.create_text(mx, top + 11, text="–", font=("Segoe UI", 10, "bold"), fill=CHALK,
                                   tags=("ui_pmin",)))
            for it in (box, mn):
                c.tag_bind(it, "<Button-1>", lambda e: (view.__setitem__("poster_small", True), show(view["tab"])))
                c.tag_bind(it, "<Enter>", lambda e: c.config(cursor="hand2"))
                c.tag_bind(it, "<Leave>", lambda e: c.config(cursor=""))
        muted = bool(J.load_json(J.STATE, {}).get("_muted"))
        btn("b_small", W - 208, H - 46, "UNMUTE AUDIO" if muted else "MUTE AUDIO", toggle_mute, size=12)

    def toggle_mute():
        s = J.load_json(J.STATE, {})
        s["_muted"] = not s.get("_muted")
        J.save_state(s)
        music.stop() if s["_muted"] else music.play()
        show(view["tab"])

    def open_support():
        __import__("webbrowser").open("https://buymeacoffee.com/pingu565")

    # ---------------- play (landing): the sheet on the left, the collage on the right
    def draw_play():
        g = gval()
        ok = bool(g and (Path(g) / "bin" / "game").exists())
        import jsgme
        mod = J.jh_mod_folder(g) if ok else None
        on = [m for m in jsgme.enabled(g) if "jungle hawks" in m.lower()] if ok else []
        keep = bool(J.load_json(J.STATE, {}).get("_keep_mounted"))
        if not ok:
            head, line, col = "Not set up", "Pick the IL-2 folder on the Settings page.", PEN_RED
        elif not mod:
            head, line, col = "Not installed", "Download it on the Install page.", PEN_RED
        elif on:
            head, line, col = "Mounted", "Enabled in JSGME. Play starts IL-2 and leaves it enabled.", PEN_GREEN
        else:
            head, line, col = "Ready", "Play mounts Jungle Hawks, starts IL-2 and puts the stock files back when the " \
                                       "game closes.", PEN_GREEN
        inst_ = J.Installer(comps, g) if ok else None
        upd = bool(inst_) and any(inst_.status(x, heads.get(x["id"])) == "Installed - Update avail"
                                  for x in comps if x.get("group") == "base")
        if head == "Ready" and upd:
            col = PEN_ORANGE
        hid = add(c.create_text(54, 116, text=head, anchor="w", font=(SERIF, 28, "bold"), fill=col))
        if head == "Ready" and upd:
            bb = c.bbox(hid)
            ua = add(c.create_text((bb[2] if bb else 170) + 16, 120, text="Update available", anchor="w",
                                   font=("Courier New", 12, "bold underline"), fill=PEN_ORANGE))
            c.tag_bind(ua, "<Button-1>", lambda e: start_install(only_base=True))      # runs the updater
            c.tag_bind(ua, "<Enter>", lambda e: c.config(cursor="hand2"))
            c.tag_bind(ua, "<Leave>", lambda e: c.config(cursor=""))
        lab = J.installed_label(on[0] if on else mod) if (on or mod) else None
        add(c.create_text(56, 168, text=lab or (on[0] if on else mod) or "", anchor="w", width=420,
                          font=("Courier New", 11, "bold"), fill="#4a3a26"))
        add(c.create_text(56, 192, text=line, anchor="nw", font=(SERIF, 11, "bold"), fill=PEN, width=410,
                          tags=("playmsg",)))
        pb = plate_btn(56, 252, "PLAY SINGLEPLAYER", start_play)
        mpb = plate_btn(56, 314, "PLAY MULTIPLAYER", lambda: start_play(multiplayer=True))
        ub = btn("b_small", 56, 382, "Unload Jungle Hawks", do_unload, size=12)
        vb = btn("b_small", 264, 382, "Revert to vanilla", do_vanilla, size=12, ink=PEN_RED)
        mb = btn("b_small", 56, 424, "Open MODS folder", open_mods, size=12)
        btn("b_tiny", 264, 425, "Changelog", show_changelog, size=11)
        pb.enable(bool(mod) and not playing["on"])
        mpb.enable(bool(mod) and not playing["on"])
        ub.enable(bool(on) and not playing["on"])
        vb.enable(ok and not playing["on"])
        mb.enable(ok)
        tick(60, 478, keep, "Keep Jungle Hawks mounted when IL-2 closes", keep_toggle)
        vr_on = bool(J.load_json(J.STATE, {}).get("_vr"))
        tick(394, 302, vr_on, "VR", vr_toggle, font=(SERIF, 16, "bold"))
        rl = add(c.create_text(394, 324, anchor="nw", font=(SERIF, 9, "bold underline"), fill="#4a3a26",
                               text={"openxr": "OpenXR", "steamvr": "SteamVR"}.get(J.vr_runtime(), "Auto")))
        c.tag_bind(rl, "<Button-1>", lambda e: show("settings"))
        c.tag_bind(rl, "<Enter>", lambda e: c.config(cursor="hand2"))
        c.tag_bind(rl, "<Leave>", lambda e: c.config(cursor=""))
        add(c.create_text(56, 498, anchor="nw", font=(SERIF, 9), fill="#4a3a26", width=410,
                          text="Multiplayer switches off only the plugins that block online play (jhhud, jhdeck) in "
                               "the mounted gbml.ini; Singleplayer puts them back. Same MODS folder, logs and backups "
                               "as JSGME (MODS\\!INSTLOGS, MODS\\!BACKUP, JSGME.ini)."))

    def show_changelog():
        """small window with CHANGELOG.md (kept current by the installer's self-update)"""
        p = J.HERE / "CHANGELOG.md"
        txt = p.read_text(encoding="utf-8", errors="replace") if p.exists() else "No changelog in this installer folder."
        w = tk.Toplevel(root)
        w.title("Jungle Hawks - changelog")
        w.configure(bg=PAPER)
        w.transient(root)
        w.geometry("560x480")
        sb = tk.Scrollbar(w)
        sb.pack(side="right", fill="y")
        t = tk.Text(w, wrap="word", bg=PAPER, fg=PEN, font=(SERIF, 11), bd=0, padx=16, pady=12,
                    yscrollcommand=sb.set)
        t.insert("1.0", txt)
        t.config(state="disabled")
        t.pack(fill="both", expand=True)
        sb.config(command=t.yview)

    def vr_toggle():
        s = J.load_json(J.STATE, {})
        s["_vr"] = not s.get("_vr")
        J.save_state(s)
        show("play")

    def set_vr_runtime(k):
        s = J.load_json(J.STATE, {})
        s["_vr_runtime"] = k
        J.save_state(s)
        show("settings")

    def keep_toggle():
        s = J.load_json(J.STATE, {})
        s["_keep_mounted"] = not s.get("_keep_mounted")
        J.save_state(s)
        show("play")

    def play_msg(m, p=None):
        later(lambda: view["tab"] == "play" and c.itemconfig("playmsg", text=m))

    def start_play(multiplayer=False):
        if not game_ok() or playing["on"]:
            return
        g = gval()
        if J.modes_state(g) == 0:
            J.enable_modes(g)
        playing["on"] = True
        music.stop()
        show("play")
        keep = bool(J.load_json(J.STATE, {}).get("_keep_mounted"))

        def work():
            try:
                vr = J.vr_runtime() if J.load_json(J.STATE, {}).get("_vr") else None
                J.play(g, unload_after=not keep, progress=play_msg, multiplayer=multiplayer, vr=vr)
                err = None
            except Exception as e:  # noqa: BLE001
                err = str(e)
                J.log(f"play: {e}")
            playing["on"] = False

            def back():
                if playing["quit"]:
                    music.close()
                    root.destroy()
                    return
                root.deiconify()
                if not J.load_json(J.STATE, {}).get("_muted"):
                    music.play()
                show("play")
                if err:
                    c.itemconfig("playmsg", text=err, fill=PEN_RED)
            later(back)
        threading.Thread(target=work, daemon=True).start()
        root.after(2500, lambda: playing["on"] and minimise(root))

    def do_unload():
        if not game_ok():
            return

        def work():
            try:
                J.unload(gval(), progress=play_msg)
                err = None
            except Exception as e:  # noqa: BLE001
                err = str(e)
                J.log(f"unload: {e}")
            later(lambda: (show("play"), err and c.itemconfig("playmsg", text=err, fill=PEN_RED)))
        play_msg("Unloading Jungle Hawks...")
        threading.Thread(target=work, daemon=True).start()

    def do_vanilla():
        """one press back to stock IL-2: every mod unloaded, JSGME backups restored, loose loader moved out, modes = 0"""
        if not game_ok() or playing["on"]:
            return
        g = gval()
        try:
            r = J.vanilla_report(g)
        except Exception as e:  # noqa: BLE001
            c.itemconfig("playmsg", text=f"Revert to vanilla: {e}", fill=PEN_RED)
            return
        lines = ["This puts IL-2 back to stock:", ""]
        lines.append("- Unload: " + (", ".join(r["mods"]) if r["mods"] else "no mods are mounted"))
        lines.append("- Restore the original game files from MODS\\!BACKUP")
        if r["orphans"]:
            lines.append(f"  (including {r['orphans']} backup(s) whose mod log was lost)")
        if r["loose"]:
            lines.append("- Move loose mod loader files out of the game: " + ", ".join(r["loose"]))
        lines.append("- Set modes = 0 in data\\startup.cfg" + (" (it is on now)" if r["modes"] == 1 else ""))
        lines += ["", "Your Jungle Hawks install in MODS stays, so Play works again later. Anything taken out of the "
                      "game is kept in MODS\\!VANILLA_REVERT_<date>, nothing is deleted.", "", "Close IL-2 first. Go?"]
        if not messagebox.askyesno("Revert to vanilla", "\n".join(lines), parent=root):
            return

        def work():
            try:
                res = J.revert_to_vanilla(g, progress=play_msg)
                err = ("Vanilla, with problems: " + "; ".join(res["problems"][:3])) if res["problems"] else None
                msg = "IL-2 is vanilla again: mods unloaded, originals restored, modes = 0."
            except Exception as e:  # noqa: BLE001
                err, msg = f"Revert to vanilla: {e}", ""
                J.log(f"revert: {e}")
            later(lambda: (show("play"),
                                   c.itemconfig("playmsg", text=err or msg, fill=PEN_RED if err else PEN_GREEN)))
        play_msg("Reverting to vanilla...")
        threading.Thread(target=work, daemon=True).start()

    def open_mods():
        if game_ok():
            mods = Path(gval()) / "MODS"
            mods.mkdir(exist_ok=True)
            os.startfile(str(mods))

    # ---------------- install: the list on the sheet, photos on the right
    def draw_install():
        inst = J.Installer(comps, gval() or None)
        src_ = J.load_json(J.STATE, {}).get("_source", "wt")
        base_ = [x for x in comps if x.get("group") == "base" and x.get("track", "1946") == src_] or \
            [x for x in comps if x.get("group") == "base"][:1]
        groups = (("Jungle Hawks", base_, PEN),
                  ("Standalone mods for the stock game", [x for x in comps if x.get("group") == "vanilla"], PEN_RED))
        y = 100
        for title, items, ink in groups:
            add(c.create_text(52, y, text=title, anchor="w", font=(SERIF, 17, "bold"), fill=ink))
            y += 34
            for comp in items:
                st = inst.status(comp, heads.get(comp["id"])) if inst.game else "Pick the IL-2 folder in Settings"
                if comp["id"] not in sel:             # installed in MODS: stays ticked until the player unticks it
                    sel[comp["id"]] = st.startswith("Installed")
                tick(56, y, sel.get(comp["id"]), comp["name"], lambda i=comp["id"]: toggle(i))
                col = PEN_GREEN if st == "Installed" else PEN_ORANGE if "Update" in st else PEN_RED if "Waiting" in st \
                    else "#6a5640"
                add(c.create_text(82, y + 19, text=st, anchor="w", font=("Courier New", 10, "bold"), fill=col))
                y += 50
            y += 8
        if not base_ or groups[1][1]:
            add(c.create_text(52, y - 2, anchor="nw", font=(SERIF, 9), fill="#4a3a26", width=420,
                              text="The standalone mods are for the stock game only - Jungle Hawks has its own."))
        have_jh = bool(inst.game) and any(inst.status(x).startswith("Installed") for x in base_)
        plate_btn(52, 470, "UPDATE" if have_jh else "INSTALL / UPDATE", start_install)
        btn("b_small", 52, 540, "Check for updates", lambda: threading.Thread(target=check_updates, daemon=True).start(),
            size=12)
        btn("b_small", 266, 540, "Add desktop shortcut", add_shortcut, size=12)

    def add_shortcut():
        def work():
            try:
                J.create_shortcut()
                J.log(f"desktop shortcut made: {J.SHORTCUT_NAME}")
            except Exception as e:  # noqa: BLE001
                J.log(f"desktop shortcut: {e}")
        threading.Thread(target=work, daemon=True).start()

    def toggle(i):
        sel[i] = not sel.get(i)
        show("install")

    # ---------------- settings: the whole sheet, two columns
    def draw_settings():
        L, R = 52, 520
        g = Path(gval()) if gval() else None
        ok = bool(g and (g / "bin" / "game").exists())
        m = J.modes_state(g) if ok else None
        add(c.create_text(L, 100, text="Paths", anchor="w", font=(SERIF, 17, "bold"), fill=PEN))
        add(c.create_text(L, 134, text="IL-2 folder", anchor="w", font=(SERIF, 12, "bold"), fill=PEN))
        e = tk.Entry(root, textvariable=game, bg=PAPER, fg=PEN, insertbackground=PEN, relief="flat",
                     font=("Courier New", 10, "bold"), highlightthickness=1, highlightbackground="#a89670",
                     highlightcolor=PEN)
        layer["widgets"].append(e)
        add(c.create_window(L, 148, window=e, anchor="nw", width=330, height=26))
        btn("b_tiny", L + 340, 144, "Browse", lambda: (game.set(filedialog.askdirectory() or gval()),
                                                        show("settings")), size=11)
        rows = [("JSGME", g / "JSGME.exe" if ok else "-", "found" if ok and J.jsgme_present(g) else "optional"),
                ("MODS folder", g / "MODS" if ok else "-", "found" if ok and (g / "MODS").exists() else "made on install"),
                ("startup.cfg", g / "data" / "startup.cfg" if ok else "-",
                 "modes = 1" if m == 1 else ("modes off" if m == 0 else "start the game once")),
                ("Download cache", J.HOME / "repos", ""), ("Log file", J.LOG, "")]
        y = 200
        for label, path, state in rows:
            add(c.create_text(L, y, text=label, anchor="w", font=(SERIF, 12, "bold"), fill=PEN))
            if state:
                add(c.create_text(L + 420, y, text=state, anchor="e", font=(SERIF, 11, "bold"),
                                  fill=PEN_GREEN if state in ("found", "modes = 1", "optional") else PEN_RED))
            add(c.create_text(L, y + 19, text=short(path, 58), anchor="w", font=("Courier New", 9, "bold"),
                              fill="#4a3a26"))
            y += 48
        add(c.create_text(R, 100, text="Game setup", anchor="w", font=(SERIF, 17, "bold"), fill=PEN))
        for i, (text, fn) in enumerate((("Enable modes = 1", lambda: act(J.enable_modes)),
                                        ("Install JSGME", lambda: act(J.install_jsgme, cfg.get("jsgme_url", ""),
                                                                      lambda m_, p_=None: None)),
                                        ("Create MODS folder", lambda: act(J.ensure_mods)),
                                        ("Open MODS folder", open_mods),
                                        ("Desktop shortcut", lambda: threading.Thread(
                                            target=lambda: J.create_shortcut(), daemon=True).start()))):
            btn("b_small", R + (i % 2) * 210, 124 + (i // 2) * 44, text, fn, size=11)
        add(c.create_text(R, 258, anchor="nw", font=(SERIF, 9), fill="#4a3a26", width=420,
                          text="modes = 1 goes into data\\startup.cfg ([KEY = system]); the first change keeps "
                               "startup.cfg.bak_jhinstaller. Close the game first."))
        add(c.create_text(R, 306, text="Build source", anchor="w", font=(SERIF, 14, "bold"), fill=PEN))
        cur = J.load_json(J.STATE, {}).get("_source", "wt")
        for i_, (key, label) in enumerate((("wt", "WT build"), ("1946", "1946 base + builder"))):
            tick(R + i_ * 150, 336, cur == key, label, lambda k=key: set_source(k))
        add(c.create_text(R, 372, text="GitHub token", anchor="w", font=(SERIF, 12, "bold"), fill=PEN))
        tokv = tk.StringVar(value=J.load_json(J.STATE, {}).get("_gh_token", ""))
        te = tk.Entry(root, textvariable=tokv, show="\u2022", bg=PAPER, fg=PEN, insertbackground=PEN, relief="flat",
                      font=("Courier New", 10), highlightthickness=1, highlightbackground="#a89670", highlightcolor=PEN)
        layer["widgets"].append(te)
        add(c.create_window(R + 120, 360, window=te, anchor="nw", width=170, height=24))
        btn("b_tiny", R + 300, 355, "Save", lambda: save_token(tokv.get()), size=11)
        add(c.create_text(R, 394, anchor="nw", font=(SERIF, 9), fill="#4a3a26", width=420,
                          text="Optional: a signed-in GitHub CLI (gh) works too. No access = the 1946 base is used."))
        add(c.create_text(R, 436, text="Aces of Thunder", anchor="w", font=(SERIF, 14, "bold"), fill=PEN))
        tick(R, 466, bool(J.load_json(J.STATE, {}).get("_aces")), "I own Aces of Thunder / have it installed",
             aces_toggle)
        add(c.create_text(R, 484, anchor="nw", font=(SERIF, 9), fill="#4a3a26", width=420,
                          text="Opens the Cockpit Overlay Builder in its own window. It runs on your PC and builds "
                               "the overlay from your own install."))
        add(c.create_text(L, 450, text="VR runtime", anchor="w", font=(SERIF, 14, "bold"), fill=PEN))
        vrk = J.vr_runtime()
        for i_, (key, label) in enumerate((("auto", "Auto"), ("steamvr", "SteamVR"), ("openxr", "OpenXR"))):
            tick(L + i_ * 120, 480, vrk == key, label, lambda k=key: set_vr_runtime(k))
        det = J.detect_vr()
        route, why = J.vr_route(vrk, det)
        found = "OpenXR: " + (det["openxr"] or "none") + "   OpenVR: " + \
                ("OpenComposite" if det["oc_system"] else "SteamVR" if det["steamvr"] else (det["openvr"] and "other")
                 or "none")
        add(c.create_text(L, 498, anchor="nw", font=("Courier New", 9, "bold"), fill="#4a3a26", width=430,
                          text=f"Found  {found}\nVR goes via {'OpenXR' if route == 'openxr' else 'SteamVR'}: {why}"))
        add(c.create_text(L, 540, anchor="nw", font=(SERIF, 9), fill="#4a3a26", width=430,
                          text="Auto picks from what this PC has. Steam copies always start through Steam. OpenXR "
                               "uses OpenComposite: its system-wide switch if on, else its dll in bin\\game for that "
                               "run only."))

    # ---------------- plugins: GB Mod Loader switches in the Jungle Hawks folder's gbml.ini
    def draw_plugins():
        L, R = 52, 560
        g = Path(gval()) if gval() else None
        ok = bool(g and (g / "bin" / "game").exists())
        ini = J.gbml_ini(g) if ok else None
        add(c.create_text(L, 100, text="Plugins", anchor="w", font=(SERIF, 17, "bold"), fill=PEN))
        if not ini or not ini.exists():
            add(c.create_text(L, 136, anchor="nw", font=(SERIF, 11, "bold"), fill=PEN_RED, width=440,
                              text="No Jungle Hawks folder with a gbml.ini in MODS. Install Jungle Hawks first."))
            return
        text = ini.read_bytes().decode("utf-8-sig")
        pend = view.setdefault("gbml", {})          # unsaved ticks: {(section, key): "0"/"1"}

        def cur(section, key):
            return pend.get((section, key), J.gbml_value(text, section, key)) == "1"

        def flip(section, key):
            new = "0" if cur(section, key) else "1"
            if new == J.gbml_value(text, section, key):
                pend.pop((section, key), None)
            else:
                pend[(section, key)] = new
            show("plugins")
        plugins = J.gbml_plugins(text)
        rows = (len(plugins) + 1) // 2
        for i, (name, _, note) in enumerate(plugins):
            x, y = (L, R - 120)[i >= rows], 134 + (i % rows) * 40
            tick(x, y, cur("plugins", name), name, lambda n=name: flip("plugins", n), font=(SERIF, 12, "bold"))
            if note:
                add(c.create_text(x + 26, y + 16, anchor="w", font=(SERIF, 8, "italic"), fill="#4a3a26",
                                  text=(lambda t: t if len(t) <= 54 else t[:51] + "...")(note.split(" = ", 1)[-1])))
        y0 = 134 + rows * 40 + 6
        add(c.create_text(L, y0, text="Multiplayer", anchor="w", font=(SERIF, 14, "bold"), fill=PEN))
        for i, (section, key, label) in enumerate(J.GBML_SWITCHES):
            tick(L + (0, 170, 420)[i], y0 + 28, cur(section, key), label, lambda s=section, k=key: flip(s, k),
                 font=(SERIF, 11, "bold"))
        fp, blocked = J.gbml_last_launch(g)
        status = (f"Last launch: MULTIPLAYER BLOCKED - {blocked}" if blocked else
                  f"Last launch fingerprint {fp}: every player and the server must show the same." if fp else
                  "Online, every player and the server must run the same plugin set: the loader compares them on join.")
        add(c.create_text(L, y0 + 50, anchor="nw", font=(SERIF, 9, "bold"), fill=PEN_RED if blocked else "#4a3a26",
                          width=680, text=status))
        btn("b_small", L, H - 82, f"SAVE PLUGINS ({len(pend)})" if pend else "SAVE PLUGINS", save_plugins, size=12)
        btn("b_small", L + 210, H - 82, "UNDO CHANGES", lambda: (pend.clear(), show("plugins")), size=12)
        btn("b_small", L + 420, H - 82, "PLUGIN FOLDER", lambda: os.startfile(str(ini.parent / "gbml")), size=12)
        add(c.create_text(L, H - 112, anchor="nw", font=(SERIF, 9), fill="#4a3a26", width=680,
                          text=view.get("gbml_msg") or f"Saves {short(ini, 60)} (first save keeps gbml.ini.bak_jhlauncher). "
                                                      "Close the game first."))

    def save_plugins():
        if not game_ok():
            return
        try:
            view["gbml_msg"] = J.gbml_save(gval(), view.get("gbml", {}))
            view["gbml"] = {}
        except Exception as e:  # noqa: BLE001
            view["gbml_msg"] = f"Not saved: {e}"
            J.log(f"plugins: {e}")
        show("plugins")

    # ---------------- aircraft information: the flight-model handbooks, one line per type
    def draw_profile(name, pdf, page, host):
        """one type: in-mod profile picture, role, the flight model's target figures, tech note + return home"""
        pic, role, code, speed, climb, power, weight, area, load, turn = PROFILES[name]
        key = "plane_" + pic
        if key not in imgs:
            imgs[key] = art(f"planes/{pic}.png")
        # laid out on the A3 landscape data sheet (art\\desk_a3.png: page 40,90 - 786,618; picture | figures rule at x 516)
        add(c.create_text(62, 180, anchor="w", font=(SERIF, 24, "bold"), fill=PEN, text=name))
        add(c.create_text(64, 210, anchor="w", font=(SERIF, 11, "bold italic"), fill=PEN_RED,
                          text=role + (f'  -  "{code}"' if code else "")))
        if imgs[key]:
            add(c.create_image(54, 226, image=imgs[key], anchor="nw"))
        add(c.create_text(64, 474, anchor="w", font=(SERIF, 11, "bold"), fill="#4a3a26",
                          text=f"In the game it flies in place of the {host}."))
        add(c.create_text(64, 494, anchor="nw", font=(SERIF, 9), fill="#4a3a26", width=430,
                          text="Figures: the published wartime data the flight model is fitted to (sources in the "
                               "technical note). The turn time is a Jungle Hawks estimate, not a flight-test figure."))
        add(c.create_text(532, 174, anchor="w", font=(SERIF, 14, "bold"), fill=PEN, text="Flight model targets"))
        rows = (("Top speed", speed), ("Climb at sea level", climb), ("Engine", power), ("Loaded weight", weight),
                ("Wing area", area), ("Wing loading", load), ("Sustained 360\u00b0 turn", turn + " (est.)"))
        y = 214
        for label, val in rows:
            add(c.create_text(532, y, anchor="w", font=(SERIF, 10, "bold"), fill="#4a3a26", text=label))
            add(c.create_text(532, y + 18, anchor="w", font=("Courier New", 11, "bold"), fill=PEN, text=val))
            add(c.create_line(532, y + 30, 770, y + 30, fill="#b8a682"))
            y += 48
        btn("b_foot", 60, 572, "\u2190 Return to list", lambda: (view.pop("profile", None), show("aircraft")), size=11)
        btn("b_foot", 242, 572, "Technical note", lambda: (view.__setitem__("viewer", (pdf, page)),
                                                           show("aircraft")), size=11)

    def draw_viewer(pdf, page):
        """the handbook as a two-page spread inside the binder (pages pre-rendered to art\\fm, no PDF library needed);
        Edge / the default PDF viewer stays available for full size"""
        tag, n = FM_PAGES[pdf]
        page = max(1, min(page, n))
        left = page if page % 2 == 1 else page - 1               # spreads: 1-2, 3-4, ... (each type starts odd)
        for i, pg in enumerate((left, left + 1)):
            if pg > n:
                continue
            key = f"fm_{tag}_{pg}"
            if key not in imgs:
                imgs[key] = art(f"fm/{tag}_{pg:02d}.png")
            x = 64 + i * 346
            if imgs[key]:
                add(c.create_rectangle(x + 4, 116, x + 340, 115 + 479, fill="#6a5a44", outline=""))
                add(c.create_image(x, 112, image=imgs[key], anchor="nw"))

        def go(to):
            view["viewer"] = (pdf, to)
            show("aircraft")
        cx = 870                                                   # controls column, right of the spread
        add(c.create_text(cx, 124, anchor="n", font=(SERIF, 12, "bold"), fill=PEN,
                          text="RAAF handbook" if tag == "raaf" else "IJN handbook"))
        add(c.create_text(cx, 148, anchor="n", font=(SERIF, 10, "bold"), fill="#4a3a26",
                          text=f"Pages {left}-{min(left + 1, n)} of {n}"))
        btn("b_tiny", cx - 55, 178, "◀ Prev", lambda: go(left - 2), size=11).enable(left > 1)
        btn("b_tiny", cx - 55, 220, "Next ▶", lambda: go(left + 2), size=11).enable(left + 2 <= n)
        btn("b_tiny", cx - 55, 262, "Full size", lambda: open_pdf(pdf, left), size=10)
        btn("b_tiny", cx - 55, 304, "← Back", lambda: (view.pop("viewer", None), show("aircraft")), size=11)

    def draw_aircraft():
        if view.get("viewer"):
            return draw_viewer(*view["viewer"])
        if view.get("profile"):
            return draw_profile(*view["profile"])
        swaps = view.get("swaps", False)
        btn("b_small", 756, 106, "Hide swaps" if swaps else "Show swaps",
            lambda: (view.__setitem__("swaps", not swaps), show("aircraft")), size=12)
        add(c.create_text(62, 108, anchor="nw", font=(SERIF, 10, "bold"), fill="#4a3a26", width=680,
                          text="Every flight model is checked against the real aircraft's published figures. Click a "
                               "type for its technical note (speed, climb, power, turn, wing loading)."
                               + ("  ↔ = stock aircraft it replaces." if swaps else "")))
        for col, (title, sub, pdf, types) in enumerate(HANDBOOKS):
            x = 62 + col * 440
            add(c.create_text(x, 158, anchor="w", font=(SERIF, 17, "bold"), fill=PEN_RED if col else PEN, text=title))
            add(c.create_text(x, 180, anchor="w", font=(SERIF, 9, "italic"), fill="#4a3a26", text=sub))
            y = 208
            for name, page, host in types:
                it = add(c.create_text(x + 6, y, anchor="w", font=(SERIF, 13, "bold"), fill=PEN, text=name))
                if swaps:                      # the stock aircraft this type flies in place of
                    pg = add(c.create_text(x + 206, y, anchor="w", font=(SERIF, 11, "bold italic"), fill=PEN_RED,
                                           text=f"↔ {host}"))
                else:
                    pg = add(c.create_text(x + 290, y, anchor="e", font=("Courier New", 10, "bold"), fill="#6a5640",
                                           text=f"p. {page}-{page + 1}"))
                for i_ in (it, pg):
                    c.tag_bind(i_, "<Button-1>", lambda e, nm=name, f=pdf, n=page, h=host:
                               (view.__setitem__("profile", (nm, f, n, h)), show("aircraft")))
                    c.tag_bind(i_, "<Enter>", lambda e, i=it: (c.config(cursor="hand2"), c.itemconfig(i, fill=PEN_RED)))
                    c.tag_bind(i_, "<Leave>", lambda e, i=it: (c.config(cursor=""), c.itemconfig(i, fill=PEN)))
                y += 30
            btn("b_small", x, 558, "Whole handbook", lambda f=pdf: (view.__setitem__("viewer", (f, 1)),
                                                                     show("aircraft")), size=12)
        if swaps:
            add(c.create_text(502, 436, anchor="nw", font=(SERIF, 10, "bold"), fill="#4a3a26", width=290,
                              text="Also in Jungle Hawks: CAC Wirraway in place of IL-2 mod.1943. The P-39L-1 and "
                                   "P-40E-1 fly as themselves. With Jungle Hawks mounted, each of these stock aircraft "
                                   "shows as its Pacific type everywhere - careers, quick missions and the AI."))

    def act(fn, *a):
        if not game_ok():
            return

        def work():
            try:
                fn(gval(), *a)
            except Exception as e:  # noqa: BLE001
                J.log(f"setup: {e}")
            later(lambda: show("settings"))
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
        g = gval()
        if not g or not (Path(g) / "bin" / "game").exists():
            show("settings")
            return False
        return True

    prompt_open = {"w": None}

    def check_updates():
        g_ = gval()
        inst_ = J.Installer(comps, g_) if g_ and (Path(g_) / "MODS").is_dir() else None
        for comp in comps:
            if not comp.get("waiting") and (comp["id"] in J.load_json(J.STATE, {})
                                            or (inst_ and inst_.unrecorded(comp))):
                heads[comp["id"]] = J.remote_head(comp)
        later(lambda: view["tab"] in ("install", "play") and not playing["on"] and show(view["tab"]))
        g_ = gval()
        if not g_ or playing["on"]:
            return
        inst_ = J.Installer(comps, g_)
        base = [x for x in comps if x.get("group") == "base"
                and inst_.status(x, heads.get(x["id"])) == "Installed - Update avail"][:1]
        if not base or heads.get(base[0]["id"]) == J.load_json(J.STATE, {}).get("_skip_update"):
            return
        try:
            man = J.assets_manifest(base[0])[0]
        except Exception as e:  # noqa: BLE001
            J.log(f"update popup: {str(e)[:160]}")
            man = {"version": heads.get(base[0]["id"])}
        notes = J.mod_changelog(J.latest_changelog())
        later(lambda: update_prompt(man, notes))

    def update_prompt(man, notes):
        """"Update to JH v2.x.x": the changelog, UPDATE and SKIP. It stays until closed; SKIP hides this version for good,
        closing the window only until the next start."""
        if playing["on"] or prompt_open["w"] is not None:
            return
        name = J.jh_version_name(man) or "the latest version"
        w = tk.Toplevel(root)
        prompt_open["w"] = w
        w.title("Jungle Hawks - update available")
        w.configure(bg=PAPER)
        w.transient(root)
        w.resizable(False, False)

        def close():
            prompt_open["w"] = None
            try:
                w.grab_release()
            except tk.TclError:
                pass
            w.destroy()
        w.protocol("WM_DELETE_WINDOW", close)
        tk.Label(w, text=f"Update to {name}", bg=PAPER, fg=PEN, font=(SERIF, 18, "bold")).pack(anchor="w", padx=18,
                                                                                            pady=(16, 2))
        sub = (man.get("label") or "").replace(name, "", 1).strip(" -:\"") if man.get("label") else ""
        if sub:
            tk.Label(w, text=sub, bg=PAPER, fg=PEN_GREEN, font=(SERIF, 11, "bold"), wraplength=520,
                     justify="left").pack(anchor="w", padx=18)
        fr = tk.Frame(w, bg=PAPER)
        fr.pack(fill="both", padx=18, pady=10)
        sb = tk.Scrollbar(fr)
        sb.pack(side="right", fill="y")
        t = tk.Text(fr, wrap="word", bg=CHALK, fg=PEN, font=(SERIF, 10), bd=0, padx=12, pady=10, width=64, height=16,
                    yscrollcommand=sb.set)
        t.insert("1.0", notes or "No changelog available.")
        t.config(state="disabled")
        t.pack(side="left", fill="both")
        sb.config(command=t.yview)
        row = tk.Frame(w, bg=PAPER)
        row.pack(fill="x", padx=18, pady=(0, 16))

        def do_update():
            close()
            start_install(only_base=True)

        def skip():
            s = J.load_json(J.STATE, {})
            s["_skip_update"] = man.get("version")
            J.save_state(s)
            J.log(f"update {man.get('version')}: skipped")
            close()
        tk.Button(row, text="UPDATE", command=do_update, bg=PEN_GREEN, fg=CHALK, activebackground=GREEN,
                  font=(SERIF, 12, "bold"), relief="flat", padx=22, pady=6, cursor="hand2").pack(side="left")
        tk.Button(row, text="SKIP", command=skip, bg=PAPER, fg=PEN, font=(SERIF, 12, "bold"), relief="groove",
                  padx=22, pady=6, cursor="hand2").pack(side="right")
        w.update_idletasks()
        w.geometry(f"+{root.winfo_rootx() + max(0, (root.winfo_width() - w.winfo_width()) // 2)}"
                   f"+{root.winfo_rooty() + max(0, (root.winfo_height() - w.winfo_height()) // 3)}")
        try:
            w.grab_set()
        except tk.TclError:
            pass
        w.focus_set()

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
            later(fn)

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
                later(on_done)
        return w, d, part, prog, state, finish

    def start_install(only_base=False):
        if not game_ok():
            return
        inst = J.Installer(comps, gval())
        src_ = J.load_json(J.STATE, {}).get("_source", "wt")
        if only_base:                                 # "Update available" on the Play page: the installed Jungle Hawks
            chosen = [x for x in comps if x.get("group") == "base" and (x["id"] in J.load_json(J.STATE, {})
                                                                        or inst.unrecorded(x))][:1]
        else:
            chosen = [x for x in comps if sel.get(x["id"]) and (x.get("group") != "base" or x.get("track", "1946") == src_)]
            # a ticked standalone mod that is installed and current is left alone (ticked only to show it is there)
            chosen = [x for x in chosen if x.get("group") == "base" or not heads.get(x["id"])
                      or inst.status(x, heads[x["id"]]) != "Installed"]
        todo = [x for x in chosen if not x.get("waiting")]
        for x in chosen:
            if x.get("waiting"):
                J.log(f"{x['name']}: not released yet - skipped")
        if not todo:
            J.log("nothing to install: select a released part")
            show("install")
            return
        s = J.load_json(J.STATE, {})
        s["_game"] = gval()
        J.save_state(s)
        w, d, part, prog, state, finish = popout("Downloading", "bg_download.png", todo, lambda: show("install"))

        def work():
            errs = []
            g = gval()
            J.ensure_mods(g)
            if not J.jsgme_present(g):
                try:
                    J.install_jsgme(g, cfg.get("jsgme_url", ""), prog)
                except Exception as e:  # noqa: BLE001
                    J.log(f"JSGME: {e}")
            for comp in todo:
                later(lambda n=comp["name"]: d.itemconfig(part, text=n))
                try:
                    try:
                        J.Installer(comps, g).install(comp, prog)
                    except J.NoAccess as e:
                        alt = next((x for x in comps if x.get("group") == "base" and x.get("track") == "1946"), None)
                        if comp.get("track") != "wt" or not alt:
                            raise
                        J.log(f"WT build: {e}. No access to the WT test build with this GitHub sign-in - installing "
                              "the 1946 base instead. Tick Aces of Thunder in Settings to build the WT parts on this PC.")
                        later(lambda n=alt["name"]: d.itemconfig(part, text=n))
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
            cmd = [x.replace("{repo}", str(p)).replace("{game}", gval()) for x in tool.get("start", [])]
            if cmd and p.exists():
                J.log("starting the Cockpit Overlay Builder")
                subprocess.Popen(cmd, cwd=p)

        go = Button(d, 300, 440 - 58, 160, 38, "Start the tool", start_tool, primary=True, font=F_TXT)
        go.enable(tid in J.load_json(J.STATE, {}))

        def dl():
            def work():
                try:
                    comp = dict(tool, id=tid)
                    J.Installer([comp], gval()).install(comp, prog)
                    later(lambda: go.enable(True))
                except Exception as e:  # noqa: BLE001
                    J.log(f"FAILED: {e}")
            threading.Thread(target=work, daemon=True).start()
        Button(d, 40, 440 - 58, 240, 38, "Download / update the tool", dl, primary=True, font=F_TXT)

    def startup_recover():
        try:
            m_ = J.recover()
        except Exception as e:  # noqa: BLE001
            J.log(f"recover: {e}")
            m_ = None
        if m_:
            later(lambda: view["tab"] == "play" and show("play"))
    root._jh_view = view               # screenshot mode toggles the swaps view
    show("play")
    threading.Thread(target=startup_recover, daemon=True).start()
    threading.Thread(target=check_updates, daemon=True).start()
    J.log(f"JH Installer {J.VERSION} started")
    if "--shot" in sys.argv:
        shots(root, c, show, popout, builder_window, Path(sys.argv[sys.argv.index("--shot") + 1]))
    root.mainloop()


def shots(root, c, show, popout, builder_window, out):
    """docs: render the views to PNG (main, settings, downloader mid-run, builder) and close. Windows are read with
    PrintWindow (no topmost, no focus grab); run only while IL-2 is closed."""
    import ctypes
    from PIL import Image

    def grab(win, name):
        win.update()
        import time
        time.sleep(0.3)
        u, g = ctypes.windll.user32, ctypes.windll.gdi32
        hwnd = u.GetParent(win.winfo_id()) or win.winfo_id()
        w, h = win.winfo_width(), win.winfo_height()
        hdc = u.GetDC(hwnd)
        mdc = g.CreateCompatibleDC(hdc)
        bmp = g.CreateCompatibleBitmap(hdc, w, h)
        g.SelectObject(mdc, bmp)
        u.PrintWindow(hwnd, mdc, 2)                       # PW_RENDERFULLCONTENT
        buf = ctypes.create_string_buffer(w * h * 4)
        hdr = (ctypes.c_uint32 * 10)(40, w, (-h) & 0xFFFFFFFF, 1 | (32 << 16), 0, 0, 0, 0, 0, 0)
        g.GetDIBits(mdc, bmp, 0, h, buf, hdr, 0)
        Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1).save(out / name)
        g.DeleteObject(bmp)
        g.DeleteDC(mdc)
        u.ReleaseDC(hwnd, hdc)

    def demo_dl():
        w, d, part, prog, state, finish = popout("Downloading", "bg_download.png", [1])
        d.itemconfig(part, text="Pingu's Jungle Hawks v2.5")
        for ln in ("Pingu's Jungle Hawks v2.5: cloning (release)", "Pingu's Jungle Hawks v2.5: receiving", "Pingu's Jungle Hawks v2.5: resolving"):
            J.log(ln)
        prog("Pingu's Jungle Hawks v2.5: Receiving objects:  64% (1532/2391), 1.21 GiB | 18.4 MiB/s", 62)
        root.after(900, lambda: grab(w, "ui_downloader.png"))
        root.after(1300, lambda: (finish("demo"), w.destroy()))
    root.after(1500, lambda: grab(root, "ui_play.png"))
    root.after(2000, lambda: show("install"))
    root.after(2500, lambda: grab(root, "ui_install.png"))
    root.after(3000, lambda: show("settings"))
    root.after(3500, lambda: grab(root, "ui_settings.png"))
    root.after(3700, lambda: show("aircraft"))
    root.after(4100, lambda: grab(root, "ui_aircraft.png"))
    root.after(4500, lambda: (root._jh_view.__setitem__("swaps", True), show("aircraft")))
    root.after(4900, lambda: grab(root, "ui_aircraft_swaps.png"))
    root.after(5000, lambda: (root._jh_view.__setitem__("profile", ("A6M2 Model 21 Zero",
                              "RAAF_Handbook_Japanese_Aircraft_Performance.pdf", 3, "LaGG-3 ser.29")), show("aircraft")))
    root.after(5500, lambda: grab(root, "ui_profile.png"))
    root.after(5600, lambda: (root._jh_view.__setitem__("viewer", ("RAAF_Handbook_Japanese_Aircraft_Performance.pdf",
                                                                     3)), show("aircraft")))
    root.after(6000, lambda: grab(root, "ui_viewer.png"))
    root.after(6400, lambda: (root._jh_view.__setitem__("poster_small", True), show("play")))
    root.after(6800, lambda: grab(root, "ui_play_poster_small.png"))
    root.after(7200, lambda: (root._jh_view.__setitem__("poster_small", False), show("install")))
    root.after(7400, demo_dl)
    root.after(9300, builder_window)
    root.after(10300, lambda: grab(root.winfo_children()[-1], "ui_builder.png"))
    root.after(10500, lambda: show("plugins"))
    root.after(10800, lambda: grab(root, "ui_plugins.png"))
    root.after(11300, root.destroy)
