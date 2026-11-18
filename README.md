# JH-Installer (local draft, 18 Nov 2026 - not on GitHub)

Python GUI (tkinter, standard library only) that installs Jungle Hawks 2.5 WT from git:

* **Base pack** (`JH-WT-Base`): the WT build without War Thunder files. Marked *Waiting* until the generator thread
  delivers the WT/non-WT split.
* **I own Aces of Thunder** (tick box): shows the swapper (`JH-Aces-Swapper`). Install clones it and starts the Aces
  Cockpit Builder, which builds `JH_PR_2.5 WT - Aces Cockpits and Optics` as the overlay on the base pack. The WT asset
  pack generator + GUI swap tool join that repo when delivered.
* **Vanilla versions** (tick box): Impact FX 2.5, Better BoX AI 2 (+ loader list), Heavy Gun Sounds 2 for the stock game.

Download: `git clone --depth 1` / `fetch` into `%LOCALAPPDATA%\JH_Installer\repos`, then the repo's `mod\` folders are
copied into `<IL-2>\MODS` (never `.git`). Without git: GitHub branch zip. Git LFS pulled when the repo uses it.

Update check (as in the Plotting Table, but on the git branch): at start and on *Check for updates*, the installed commit
is compared with `git ls-remote <repo> refs/heads/<branch>` (GitHub API without git). It never updates by itself; the
line shows **Installed - Update avail** and the user presses *Install / Update*. A folder JSGME has enabled
(`MODS\!INSTLOGS\<name> install.log`) is never written.

Test: `python -I jh_installer.pyw --selftest` (local repos, fake game folder, temp state).
Parts and repo URLs: `components.json`. State/log: `%LOCALAPPDATA%\JH_Installer`.
