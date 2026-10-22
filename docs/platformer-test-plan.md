# Storm Night browser playthrough test plan

Scope: authored resources in `Storm Night` (`project/scenes/storm_night/`), its five house actors, four splice pickups, six hazard triggers, and project settings. The final GBC-only ROM built successfully; the pickup/repair sequence still needs a complete live playthrough.

Status labels: **Source-confirmed** means the behavior/text is present in authored resources; **Live test** means verify it in the open browser because source inspection cannot confirm runtime input, collision, presentation, or audio.

## Manual playthrough

1. **Start and controls.** Launch the project from its configured start, Storm Night at `(2,32)`. Check that the opening help says “Move: D-pad”, “Jump: A”, “B: CONNECT / CUT”, and “B: PICK UP”; dismiss the help with A. The scene starts `cfe_village_1`, initializes `HOMES 0 / 5` and `SPLICES 1 / 5`, and shows both on the overlay. **Source-confirmed:** project start, engine input fields, scene script, initial music and HUD templates. **Live test:** verify the prompts, counter values, D-pad movement, A jump, B interaction, and audio in-browser.

2. **Substation, pickup, and first repair.** The player starts beside the Substation actor at `(1,32)`, whose dialogue is “Grid starts here.” The initial splice inventory is 1. B collects a loose splice and increments `Splices Held`; the lower-platform pickup is at `(5,32)`. Marta’s house at `(3,29)` requires `Connected Houses == 0` and at least one splice; a successful repair consumes one splice, increments the home counter, changes to “Marta Powered”, and shows her two fixed cable actors. **Source-confirmed:** pickup script, inventory gate/consumption, positions, house gate and resulting actor changes. **Headless-tested:** a pickup increased inventory from 1 to 2; the first repair changed homes to 1 and inventory to 1; cutting reset homes to 0 and refunded inventory to 2. **Live test:** verify the same sequence and rendered counters in-browser.

3. **Marta → Tomas (home 2).** Collect another splice from the mid-platform pickup at `(11,23)`, then go to Tomas’s House `(14,26)`. Its gate is `1`; it consumes a splice, increments homes to `2`, powers Tomas and shows his cable pair. The music changes to `cfe_village_2`. **Source-confirmed:** pickup/inventory and order gates, scripts, HUD draw and music event at count 2. **Live test:** traversal, pickup, repair and visible/audio results.

4. **Rosa (home 3).** Collect a splice from the upper-middle pickup at `(10,26)`, then reach Rosa’s House `(5,23)`. The gate is `2`; it consumes a splice, increments homes to `3`, powers Rosa and shows her cable pair. The authored stage remains `cfe_village_2`. **Source-confirmed:** gate/actions and no new music event at 3. **Live test:** verify in-browser.

5. **Kiko (home 4).** Collect a splice from the high-platform pickup at `(7,17)`, then reach Kiko’s House `(12,20)`. The gate is `3`; it consumes a splice, increments homes to `4`, powers Kiko and shows his cable pair. The music changes to `cfe_village_3`. **Source-confirmed:** gate/actions and music event at count 4. **Live test:** verify in-browser.

6. **Nuria (home 5) and win.** At Nuria’s House `(8,17)`, the gate is `4`; it consumes the remaining splice, increments homes to `5`, powers Nuria and shows her cables. The script sets Game State to `1`, plays `cfe_win`, and displays “Grid restored! All five are lit!” Check final `HOMES 5 / 5`, `SPLICES 0 / 5`. **Source-confirmed:** final gate, state/music/dialogue/HUD events. **Live test:** verify the full ending presentation and that further interactions do not undo the win.

7. **Death/respawn and hazard coverage.** Before completing the run, deliberately enter each authored hazard trigger and verify the player returns to `(2,32)`: Hazard 1 `(17,31; 3×1)`, 2 `(6,28; 2×1)`, 3 `(15,25; 2×1)`, 4 `(0,22; 2×1)`, 5 `(14,19; 2×1)`, 6 `(4,16; 3×1)`. Each trigger plays a sound and sets the player position to the start; none of these trigger scripts changes the home counter or game state. **Source-confirmed:** all six bounds and the two trigger actions. **Live test:** confirm each region is entered as a hazard, the sound/respawn work, and progress/HUD persist.

8. **HUD consistency.** At each pickup, repair, cut and respawn, check both `HOMES 0–5 / 5` and `SPLICES 0–5 / 5`. Scene, pickup, and house scripts draw the counters after each relevant change. **Source-confirmed:** HUD text-draw events. **Live test:** confirm dynamic values, placement, legibility and persistence on the actual browser display.

## Deferred sample-derived loop elements

- **Truck/substation intro:** no truck actor or scripted intro sequence is present in Storm Night. The scene begins with setup, music and controls help; the Substation is a static actor with “Grid starts here.” **Deferred.**
- **Exact 1/10 sample counter:** adapted to a truthful `SPLICES 1 / 5` held-splice inventory because this brief has five homes. The game starts with one splice and four additional pickups. **Source-confirmed; live collection still needs testing.**
- **Free-form tether:** the five house scripts show/hide two fixed cable actors per house; no player-carried connector or free-form tether behavior is authored in these resources. **Deferred.**

## MCP source snapshot

Project `mr-cfe` was selected at source revision `89a482c06c3a6965b206469668ce80068adc3d523175d0000964e3c959d5b556`. MCP reported zero project errors and warnings, start scene Storm Night at `(2,32)`, 20 scene actors, 6 hazard triggers, and an authored static estimate of 38/40 OAM objects. The five house gates are Marta `0`, Tomas `1`, Rosa `2`, Kiko `3`, Nuria `4`; music stages change at 2 and 4, with the final win branch at 5. The six hazard triggers all use sound-and-teleport actions. A GBC-only ROM built successfully; PyBoy confirmed the lower pickup, first repair, and cut/refund state changes. The complete five-house/hazard run and browser or physical-device review remain pending. The existing browser preview was left open and unchanged.
