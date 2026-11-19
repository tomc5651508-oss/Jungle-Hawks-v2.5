Pingu's Jungle Hawks - changelog

MOD

JH v2.5.2  (19 Nov 2026)
- Gun belts now match each gun's calibre on 9 planes.
  Japanese 7.7 mm guns fire 7.7 mm rounds (they had 7.92 / 7.62 mm),
  the Ho-103 fires 12.7 mm (it had 20 mm), the IL-2's M2 fires 12.7 mm (it had 20 / 23 mm).

JH v2.5.1  (18 Nov 2026)
- Fixed the swapped planes failing to load (#10003): planeint now mode = uniform.

JH v2.5  (18 Nov 2026)
- Public release of JH v2.5.

INSTALLER / LAUNCHER

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
