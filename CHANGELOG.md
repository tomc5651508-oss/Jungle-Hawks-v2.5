Pingu's Jungle Hawks - changelog

MOD

JH v2.5.5  (19 Nov 2026)
- planeint 1.5.2: online, the modified planes skip the plane-script check in sessions the GB Mod
  Loader handshake verified (fixes #10003 when spawning on a JH server). gbml_log shows scriptcrc 1.5.2.

JH v2.5.2  (19 Nov 2026)
- Gun belts now match each gun's calibre on 9 planes.
  Japanese 7.7 mm guns fire 7.7 mm rounds (they had 7.92 / 7.62 mm),
  the Ho-103 fires 12.7 mm (it had 20 mm), the IL-2's M2 fires 12.7 mm (it had 20 / 23 mm).

JH v2.5.1  (18 Nov 2026)
- Fixed the swapped planes failing to load (#10003): planeint now mode = uniform.

JH v2.5  (18 Nov 2026)
- Public release of JH v2.5.

INSTALLER / LAUNCHER

1.0.14
- VR runtime: new Auto setting (the default) picks from what the PC has: the active OpenXR runtime
  (SteamVR, Virtual Desktop, Meta, WMR, Pimax, Varjo...) and whether OpenComposite is switched on for
  all games. Settings shows what it found and which way VR will start.
- OpenXR now starts IL-2 directly with its VR switches instead of through Steam's VR mode, so SteamVR
  no longer starts alongside another runtime (black screen, "unsupported apptype 3" errors).
  With OpenComposite switched on for all games, the game's own openvr_api.dll is kept.

1.0.13
- Play page: VR tick next to the Play buttons. With it ticked, both Play buttons start IL-2 in VR.
- Settings: VR runtime, SteamVR (default) or OpenXR. SteamVR uses Steam's Launch in VR. OpenXR uses
  OpenComposite: the launcher downloads its openvr_api.dll once, swaps it into bin\game for that run
  and puts the game's own back when IL-2 closes.

1.0.12
- The Aircraft Info tab now hangs from the bottom edge, centred, so it no longer covers the title art.

1.0.11
- Play page: PLAY SINGLEPLAYER and PLAY MULTIPLAYER. Multiplayer switches off only jhhud and jhdeck
  (they do not start on the current IL-2 build, and a plugin that fails blocks online play) in the
  mounted gbml.ini; every other line stays as it is. Singleplayer puts them back.
- New Plugins tab: switch GB Mod Loader plugins and the multiplayer handshake settings, and see the
  last launch's multiplayer fingerprint or why multiplayer was blocked.

1.0.10
- Fixed silent guns: Play now checks the game is using Jungle Hawks' own sound bank before starting.
  Every Jungle Hawks gun sound lives only in that bank, so another bank (stock, Heavy Gun Sounds,
  The 8th Airforce, an older Jungle Hawks) meant guns firing with no sound. Play says what replaced it
  and points to Revert to vanilla. Also catches stock-game mods enabled in JSGME after Jungle Hawks.

1.0.9
- The 8th Airforce (B-17, stock game) can be downloaded from the Install page.
- Mods already installed in MODS now show ticked on the Install page. Pressing Update leaves
  ticked mods that are already current alone.
- Play refuses to start Jungle Hawks while a stock-game mod (Impact FX, Better BoX AI, Heavy Gun Sounds,
  The 8th Airforce) is enabled in JSGME, because they write the same files. Disable it or press Revert to vanilla.

1.0.8
- New "Revert to vanilla" button on the Play page: one press puts IL-2 back to stock.
  It unloads every mounted mod, puts the original game files back from MODS\!BACKUP
  (also backups whose mod log was lost, and half-finished mounts), moves loose mod loader files
  (winmm.dll, GBML.dll, gbml folder) out of bin\game, and sets modes = 0.
  Nothing is deleted: anything taken out goes to MODS\!VANILLA_REVERT_<date>. Play works again afterwards.
- Unload no longer stops at the first locked file: it retries, finishes the rest, and says what is left.
- Unload also finds Jungle Hawks when JSGME.ini is missing or out of step.

1.0.7
- Fixed "CERTIFICATE_VERIFY_FAILED" on some PCs: downloads now check certificates against Windows' own list
  plus a built-in list of trusted roots.

1.0.6
- Non-Steam IL-2 (1C installer) is found by itself, and Play starts its own launcher instead of Steam.

1.0.5
- Installer updates now show in a small window with a progress bar, then the launcher reopens.
- "Update available" on the Play page is a button: it updates Jungle Hawks.
- Install page: the big button says UPDATE once Jungle Hawks is installed.
- "Add desktop shortcut" button on the Install page.

1.0.4
- Changelog names each release JH v2.5.X.

1.0.3
- Changelog button on the Play page.

1.0.2
- Play page: "Ready" is green when Jungle Hawks is up to date, orange with
  "Update available" beside it when a newer version is out.

1.0.1
- Updates itself when it starts.
- Fixed HTTP 403 errors (downloads no longer use GitHub's limited API).
- Fixed HTTP 416 errors when a part had already finished downloading.
- Fixed "No such file or directory" on long file paths in the MODS folder.
- Heavy Gun Sounds: the sound bank now downloads in full.

1.0.0
- First release.
