# Better BoX AI - the Jungle Hawks AI

*Pingu's BFMs and Bugouts. Ships inside Pingu's Jungle Hawks v2.5, and as a standalone mod for the stock game
(Pingus Better BoX AI 2 - vanilla).*

Stock Great Battles AI flies as individuals. Better BoX AI makes flights fly as flights: a leader and his wingmen
that cover each other, take turns on a target, break off when it goes bad and come home together.

## What it changes

- **Flights, not individuals** - the leader picks the fight; wingmen cover the shooter, take hand-offs and rejoin
  when they drift more than 1.2 km off the lead
- **Attack sequences** - fighters set up from height and the sun, make passes and extend instead of turning circles
  on the deck; bombers keep formation and gunners concentrate
- **Gunnery** - aim error and opening range scaled by skill, so an ace shoots like one and a novice sprays
- **Sun glare** - attackers out of the sun are harder to see
- **Bugouts** - after a disengage the flight holds its cruise formation on the way home for 150 s instead of turning
  back into the fight; a bandit on the flight inside 1 km still gets a short fight; out of ammo means going home
- **Self-defence always wins** - no rule stops an AI defending itself

## Jungle Hawks only

With the Jungle Hawks plugins loaded the AI also knows the Pacific aircraft (their own speed rows and flight names)
and flies the refitted performance tables, so AI and player fly the same aircraft. Career missions start the flight
in the air 14 km from the objective instead of anywhere up to 150 km away, and fighter squadrons get more short
intercepts and airfield scrambles.

## Settings and logs

- `bin\game\gbml\bbai.ini` - every switch and distance, commented
- `bin\game\gbml\bbai_log.txt` - what each flight decided and why ("flight: ... egress", "cover", "hand-off")
- Combat CSV in `bin\game\gbml\` for anyone who wants the numbers

## Status

Part of the v2.5 playtest. Report odd AI with the mission, a screenshot and `bbai_log.txt`.
