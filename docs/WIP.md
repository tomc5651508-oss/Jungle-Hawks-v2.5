# Work in progress - what is not finished in v2.5

Pingu's Jungle Hawks v2.5 is a playtest release. This page lists what is known to be unfinished or untested, so
nobody loses an evening to it. Reports on any of these are welcome.

## Planned features on test assets

- **Carrier task forces** - Shokaku and Enterprise with their escorts, deck take-offs and landings and aerial
  torpedoes are planned features running on test assets and designs. Please play them and send feedback - what
  works, what breaks, what you want next.

## Not tested yet

- **Online multiplayer** - the mod-matched handshake and the dedicated-server kit are built but have not been run
  on a public server. Expect rough edges; play with friends who run the identical version.
- **Stock-game standalone mods** - the vanilla Impact FX, Better BoX AI and Heavy Gun Sounds packages are built
  for the stock game but have not been flown there yet.

## Known open items

- **Bomb bays** - on a few bombers the far LODs (seen from a distance) still show the bay roof open.
- **Skins** - several types still carry first-pass skins; a proper repaint needs a skin artist (volunteers welcome).
- **Some features are only in the private test build** - tactical codes painted by the game, the hangar skin swap
  and a few re-seated crews live in the private test build and are not in the public base pack yet.
- **Turn figures** - the sustained-turn targets in the flight model handbooks are Jungle Hawks estimates from the
  published data, not flight-test figures.

## Cockpits and meshes - the optional builder

The public pack ships the cockpits and airframes Jungle Hawks has always had. Players who own a certain other
combat flight title will find an extra option in the installer's Settings - you will know it when you see it.

**What it does:** a small builder runs on your own PC, reads your own local install of that title, converts the
cockpits it finds (meshes, sights, gauges and their animation bindings) to the Great Battles format and writes the
result as a new, inactive JSGME mod folder. Nothing from it is downloaded from us; your copy exists only on your PC.

**Risks - read before you use it:**

- **Unofficial and personal use only.** Never share or upload the folder it builds.
- **Updates break it.** A patch to either game can change the files it reads; rebuild after updates, and expect
  the occasional cockpit that comes out wrong.
- **Multiplayer:** other players do not have your built cockpits. Use it offline, or expect the handshake to refuse
  a server that checks files.
- **Disk:** the source data is large; keep a few GB free on the game drive.
- **Undo:** the output is a normal JSGME folder. Disable it in JSGME (or Unload in the launcher) and the game's own
  files come back from the JSGME backup.
- When reporting a bug, say whether the built cockpits were enabled - and do not attach the built folder.
