Pingu's Jungle Hawks - changelog

MOD

JH v2.6.5  (20 Nov 2026)
- A6M2 Zero fires again: its trigger was still wired the Fw 190 way, which its host plane ignores. Every
  Japanese plane and turret was audited for the same kind of left-over gun settings; the A6M2 cannon
  modes and the Ki-61 pod and wing gun modes are fixed too.
- A6M3: cannon set back to the Type 99-1 (the likely cause of the crash at mission start).
- Corsair and Wildcat cockpits: glass no longer frosted, and the cockpit has less contrast and glare.
- Gunsights lined up: Dauntless telescope, Ki-43, Ki-61 and Ki-45.
- Dauntless, Mustang and Avenger: the outside model no longer shows in the cockpit with the Aces
  cockpits on.
- Online: the Bean Bot server runs v2.6.5, so update before joining.

JH v2.6.4  (20 Nov 2026)
- Corsair: the gunsight now lines up. The eye sits on the sight line, the reticle lies on the
  reflector glass, and the double cockpit from the outside model stays gone.
- Online: the Bean Bot server runs v2.6.4, so update before joining.

JH v2.6.3  (20 Nov 2026)
- New plugin "jhradio": an SRS radio panel on the briefing screen (key O) for multiplayer. Pick radio 1,
  radio 2 or intercom, change channel and volume, mute. Needs the IL-2 SimpleRadio Standalone client
  (controls set to HOTAS); talk with your SRS PTT key. Off by default: turn it on in the launcher's
  Plugins tab. It does nothing in single player.
- Corsair and Avenger: the outside model's cockpit no longer draws over the cockpit view.

JH v2.6.2  (20 Nov 2026)
- Guadalcanal campaign: Japanese squadrons fly from their own airfields (Rekata Bay and Santa Isabel
  South) instead of the old airfield location.
- Japanese squadrons no longer show German insignia.
- Every added Japanese plane and turret uses its host airframe's stock guns and ammunition, with
  historical loads.
- Cockpit glass fixed in 7 cockpits, including the Wildcat and Corsair.

JH v2.6.1  (19 Nov 2026)
- The 7.7 mm green tracer guns from v2.6 were rolled back. The Zeros (A6M2, A6M3, A6M5) use stock
  machine guns with stock ammunition.

JH v2.6 - "stuff i forgot to merge lol" update  (19 Nov 2026)
- Japanese 7.7 mm machine guns had no ammunition (they were fed .303 / 7.69 mm rounds). They now fire
  7.7 mm rounds with a green tracer, on the fighters (A6M2, A6M3, A6M5) and the bomber turrets
  (D3A, G4M, Ki-21, Ki-45).
- B-17 crew seating fixed.
- Guadalcanal campaign: historical objectives.

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

1.0.21
- Fixed: with the Aces cockpits on, joining a server was refused (back to mode selection, no error). The
  mod loader checks the plane scripts again when you join, so the Aces gunsight lines now go in only after
  the join is verified, and Jungle Hawks' come back when the session ends, ready for the next join.
- With the Aces cockpits on, only their view lines are used (gunsight position, pilot head position, cockpit
  sphere): guns, belts and flight model always stay the current Jungle Hawks ones. Works with the new
  delta-only Aces pack (aces_gunsight_delta.json) and with older packs.
- Fixed the launcher log growing huge (one line per update tick after a download window was closed).

1.0.20
- Play page tidied: "Aces cockpits on top (singleplayer)" moved down under "Keep Jungle Hawks
  mounted"; VR stays beside the Play buttons on its own.
- Start SRS button: orange ring when the jhradio plugin is on; green ring and "SRS on" while the SRS
  client runs (checked every 5 s). With the plugin off there is no ring, and SRS can still be started.
- The Aces cockpits box shows only when the Aces cockpit folder was in MODS when the launcher started.
- Aces cockpits now work in Play Multiplayer too: for an online session the 5 plane scripts the Aces
  cockpits change (only their gunsight line) start as Jungle Hawks' own, so the mod loader's online check
  matches the server. Once the loader has done that check, the Aces gunsight lines go back in, so the sight
  lines up in the Aces cockpits online too.

1.0.19
- Play page "Aces cockpits" box (shown when the Aces cockpit folder is in MODS): ticked, Play rolls it
  in on top of Jungle Hawks and takes it off again when IL-2 closes. Left off for Play Multiplayer
  (its changed plane scripts would not match the server).
- SRS: "Start SRS" button and "SRS active" (green when the jhradio plugin is on) on the Play page; SRS
  client path in Settings (also used by the in-game START SRS button); Install page link to the SRS
  website.

1.0.18
- Fixed the launcher window crashing (a Tcl/Tk memory error) while IL-2 runs or an update checks: only
  the window's own thread touches the window now.
- When a Jungle Hawks update is out, a window says "Update to JH v2.x.x" with the changelog and
  UPDATE / SKIP buttons. SKIP hides that version; closing the window shows it again next start.
- A Jungle Hawks folder that is in MODS but was not installed by this launcher (copied by hand,
  or by an old installer) now shows "Update available" instead of "Not installed", so the update
  to the latest JH version is offered.

1.0.17
- The Play page shows the name of the installed Jungle Hawks update (JH v2.6 "stuff i forgot to
  merge lol" update).

1.0.16
- Steam copies always start through Steam, VR with OpenXR included (Launch in VR). Only non-Steam
  copies start Il-2.exe directly.

1.0.15
- Non-Steam IL-2: Play now starts the game itself (bin\game\Il-2.exe) instead of the 1C launcher.
  The 1C launcher tries to patch the game files from 1C's update server; with Jungle Hawks mounted
  those files are not stock, its download fails (HTTP 416) and the game dies with "alloc: invalid
  block". To update IL-2 itself, unload Jungle Hawks first, then run the 1C launcher.
- Downloads: an HTTP 416 on a part that is already complete is accepted instead of failing, and a
  part file held by another installer window or a virus scanner gets a clear message.

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
