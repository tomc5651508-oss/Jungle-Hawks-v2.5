# JH-Installer

The public download for Jungle Hawks. Players get `JH-Installer-<version>.zip` from the Jungle-Hawks Releases page,
unzip it and run `Start JH Installer.bat`. Python 3.10+ standard library only (tkinter); Git for Windows optional.

## What it does

- **Install tab:** cards for Jungle Hawks and the three standalones (Impact FX, Better BoX AI, Heavy Gun Sounds -
  stock game only). Install / Update pops out a download window: old-photo background with the colour picture
  sweeping in as the progress bar, current step and live log.
- **Settings tab:** IL-2 folder (found via Steam), JSGME / MODS / startup.cfg / cache / log paths with status;
  buttons for Enable modes = 1 (backs up `data\startup.cfg` first), Install JSGME (needs `jsgme_url`),
  Create MODS folder, Desktop shortcut; "I own Aces of Thunder" opens the Cockpit Overlay Builder window.
- **Updates:** at start, the installed commit of each part is compared with the head of its `release` branch
  (`git ls-remote`, GitHub API without git). Nothing updates by itself; the card shows *Installed - Update avail*.
- **Safety:** only the repo's `mod\` folders are copied into MODS (never `.git`); a folder JSGME has enabled
  (`MODS\!INSTLOGS\<name> install.log`) is never written.
- **Desktop shortcut "Il2∶ Jungle Hawks"** (`jh_launch.pyw`, icon `art\jh_launch.ico`): warns when Jungle Hawks is not
  enabled in JSGME, asks before setting modes = 1, then starts IL-2 through Steam.

## Files

| File | Role |
|---|---|
| `jh_installer.pyw` | logic: game/JSGME/startup.cfg, git/zip download with progress, copy into MODS, update check, shortcut |
| `ui.py` | the canvas UI (main window, Settings, pop-out downloader, Cockpit Overlay Builder window) |
| `jh_launch.pyw` | the Desktop shortcut's launcher |
| `components.json` | parts (repo, branch `release`, MODS folder names), `jsgme_url`, `cockpit_builder` |
| `art\` | backgrounds pre-rendered from the mod's loading-screen shots and main-menu logo; shortcut icon |
| `selftest.py` | `python -I jh_installer.pyw --selftest` - local repos, fake game folder, temp state |

State and log: `%LOCALAPPDATA%\JH_Installer`. Screenshots for docs: `python jh_installer.pyw --shot <folder>` (needs Pillow).
