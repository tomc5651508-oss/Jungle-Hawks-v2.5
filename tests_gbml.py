r"""offline tests for the Plugins tab helpers in jh_installer.pyw (gbml.ini read / switch / save) on a temp game folder"""
import os, sys, tempfile
from pathlib import Path

tmp = Path(tempfile.mkdtemp(prefix="gbml_t_"))
os.environ["JH_INSTALLER_HOME"] = str(tmp / "home")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import jh_installer as J  # noqa: E402

checks = 0


def check(ok, what):
    global checks
    if not ok:
        raise SystemExit("FAILED: " + what)
    checks += 1
    print("PASS", what)


INI = ("; JH settings\r\n[loader]\r\nenabled=1\r\n\r\n[multiplayer]\r\nhandshake=1\r\nstrict=1\r\n\r\n[plugins]\r\n"
       "; jhhud = marker colours\r\njhhud=1\r\n; jhdeck = carrier decks\r\njhdeck = 1  \r\njhhud=0\r\nfmfix=1\r\n")


def main():
    p = J.gbml_plugins(INI)
    check([n for n, _, _ in p] == ["jhhud", "jhdeck", "fmfix"] and all(on for _, on, _ in p),
          "plugins listed in order, first line of a doubled plugin wins like the loader")
    check(p[0][2] == "jhhud = marker colours" and p[2][2] == "", "notes above a line become its description")
    check(J.gbml_set(INI, "plugins", "jhdeck", "0") == INI.replace("jhdeck = 1  ", "jhdeck = 0  "),
          "a switch changes only that value and keeps notes, spacing and CRLF")
    check(J.gbml_set(INI, "plugins", "jhhud", "0").count("jhhud=0") == 2, "only the first doubled line changes")
    check(J.gbml_value(J.gbml_set(INI, "multiplayer", "kick", "0"), "multiplayer", "kick") == "0"
          and "strict=1\r\nkick=0\r\n\r\n[plugins]" in J.gbml_set(INI, "multiplayer", "kick", "0"),
          "missing key goes at the end of its section")
    check(J.gbml_set("[loader]\nenabled=1\n", "plugins", "x", "1") == "[loader]\nenabled=1\n[plugins]\nx=1\n",
          "missing section added before the trailing newline")
    for bad in (("plugins", "jhhud", "1\r\n[x]"), ("plugins", "../evil", "1")):
        try:
            J.gbml_set(INI, *bad)
            check(False, "bad input refused")
        except ValueError:
            check(True, f"bad input refused: {bad[1]!r} = {bad[2]!r}")
    game = tmp / "game"
    mod = game / "MODS" / "Pingu's Jungle Hawks v2.5"
    (mod / "bin" / "game").mkdir(parents=True)
    (game / "bin" / "game").mkdir(parents=True)
    (mod / "bin" / "game" / "gbml.ini").write_bytes(INI.encode())
    (game / "bin" / "game" / "gbml.ini").write_bytes(INI.encode())          # mounted copy
    J.il2_running = lambda: False
    check(J.gbml_ini(game) == mod / "bin" / "game" / "gbml.ini", "the JH folder's gbml.ini in MODS is the one edited")
    msg = J.gbml_save(game, {("plugins", "jhhud"): "0", ("plugins", "jhdeck"): "0"})
    want = INI.replace("jhhud=1", "jhhud=0", 1).replace("jhdeck = 1  ", "jhdeck = 0  ")
    check((mod / "bin" / "game" / "gbml.ini").read_text(newline="") == want, "save writes the switched values")
    check((game / "bin" / "game" / "gbml.ini").read_text(newline="") == want and "mounted" in msg,
          "a mounted identical copy is updated too")
    check((mod / "bin" / "game" / "gbml.ini.bak_jhlauncher").read_bytes() == INI.encode(), "first save keeps a backup")
    (game / "bin" / "game" / "gbml.ini").write_text("someone else's\n")
    J.gbml_save(game, {("plugins", "fmfix"): "0"})
    check((game / "bin" / "game" / "gbml.ini").read_text() == "someone else's\n",
          "a live gbml.ini that is not the mounted JH copy is left alone")
    check(J.gbml_save(game, {("plugins", "fmfix"): "0"}) == "No plugin changes to save.", "no-op save writes nothing")
    J.il2_running = lambda: True
    try:
        J.gbml_save(game, {("plugins", "fmfix"): "1"})
        check(False, "save refused while IL-2 runs")
    except RuntimeError:
        check(True, "save refused while IL-2 runs")
    J.il2_running = lambda: False
    mpini = INI.replace("jhdeck = 1  ", "jhdeck = 0  ")
    (mod / "bin" / "game" / "gbml.ini").write_bytes(b"\xef\xbb\xbf" + mpini.encode())
    J.gbml_multiplayer(game)
    check((mod / "bin" / "game" / "gbml.ini").read_bytes() == b"\xef\xbb\xbf" + mpini.replace("jhhud=1", "jhhud=0", 1).encode(),
          "Play Multiplayer: jhhud=0 / jhdeck=0, every other byte (BOM, CRLF, notes, other plugins) unchanged")
    (mod / "bin" / "game" / "gbml.ini").write_bytes(b"[plugins]\nfmfix=1\n")
    check(J.gbml_multiplayer(game) == "No plugin changes to save."
          and (mod / "bin" / "game" / "gbml.ini").read_bytes() == b"[plugins]\nfmfix=1\n",
          "Play Multiplayer adds no jhhud / jhdeck line when they are not listed")
    J.il2_running = lambda: True
    (mod / "bin" / "game" / "gbml.ini").write_bytes(INI.encode())
    try:
        J.gbml_multiplayer(game)
        check(False, "Play Multiplayer refused while IL-2 runs")
    except RuntimeError:
        check((mod / "bin" / "game" / "gbml.ini").read_bytes() == INI.encode(), "Play Multiplayer refused while IL-2 runs")
    (game / "bin" / "game" / "gbml_log.txt").write_text(
        "2026-01-01 00:00:00.000 [gbml] ---- GB Mod Loader 1.5.0 starting in x\n"
        "2026-01-01 00:00:01.000 [gbml] MULTIPLAYER BLOCKED: plugin(s) jhdeck count for the match\n"
        "2026-02-01 00:00:00.000 [gbml] ---- GB Mod Loader 1.5.0 starting in x\n"
        "2026-02-01 00:00:01.000 [gbml-mp] fingerprint GBML1:c3d363287722a6a0... (5 plugin(s))\n")
    check(J.gbml_last_launch(game) == ("GBML1:c3d363287722a6a0", ""), "only the last launch's fingerprint / block counts")
    print(f"ALL {checks} GBML CHECKS PASSED")


if __name__ == "__main__":
    main()
