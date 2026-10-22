# Storm Night browser playthrough test plan

Scope: authored resources in `Storm Night` (`project/scenes/storm_night/`), its five house actors and six hazard triggers, plus project settings. No gameplay was run during this review.

Status labels: **Source-confirmed** means the behavior/text is present in authored resources; **Live test** means verify it in the open browser because source inspection cannot confirm runtime input, collision, presentation, or audio.

## Manual playthrough

1. **Start and controls.** Launch the project from its configured start, Storm Night at `(2,32)`. Check that the opening help says “Move: D-pad”, “Jump: A”, and “B: PULL CABLE”; dismiss the help with A. The scene starts `cfe_village_1` and draws `HOMES 0 / 5` (the authored format is `HOMES %D0$01$ / 5`). **Source-confirmed:** project start, scene script, help text, initial music and HUD template. **Live test:** verify the prompt, HUD rendering, D-pad movement, A jump/dismiss, and audio in-browser.

2. **Substation and first repair.** The player starts beside the Substation actor at `(1,32)`, whose only authored dialogue is “Grid starts here.” Dismiss it with A; follow the help prompt and try B at the first cable/house interaction. The first house gate is Marta (house at `(3,29)`): its script accepts `Connected Houses == 0`, increments the counter, changes to “Marta Powered,” and shows Marta’s two fixed cable actors. **Source-confirmed:** positions, dialogue, counter gate and resulting actor changes. **Live test:** verify B actually invokes the interaction, whether the substation is reached first, and the visible repair/HUD change to `1 / 5`.

3. **Marta → Tomas (home 2).** After Marta, go to Tomas’s House `(14,26)`. Its gate is `1`; it increments to `2`, powers Tomas and shows his cable pair. Check that the HUD reads `2 / 5` and the music changes to `cfe_village_2`. **Source-confirmed:** order/gates, scripts, HUD draw template and music event at count 2. **Live test:** traversal, interaction and visible/audio results.

4. **Rosa (home 3).** At Rosa’s House `(5,23)`, the gate is `2`; it increments to `3`, powers Rosa and shows her cable pair. Check `3 / 5`; the authored stage remains `cfe_village_2`. **Source-confirmed:** gate/actions and no new music event at 3. **Live test:** verify in-browser.

5. **Kiko (home 4).** At Kiko’s House `(12,20)`, the gate is `3`; it increments to `4`, powers Kiko and shows his cable pair. Check `4 / 5` and the change to `cfe_village_3`. **Source-confirmed:** gate/actions and music event at count 4. **Live test:** verify in-browser.

6. **Nuria (home 5) and win.** At Nuria’s House `(8,17)`, the gate is `4`; it increments to `5`, powers Nuria and shows her cables. The script sets Game State to `1`, plays `cfe_win`, and displays “Grid restored! All five are lit!” Check final `5 / 5` HUD. **Source-confirmed:** final gate, state/music/dialogue/HUD events. **Live test:** verify the full ending presentation and that further interactions do not undo the win.

7. **Death/respawn and hazard coverage.** Before completing the run, deliberately enter each authored hazard trigger and verify the player returns to `(2,32)`: Hazard 1 `(17,31; 3×1)`, 2 `(6,28; 2×1)`, 3 `(15,25; 2×1)`, 4 `(0,22; 2×1)`, 5 `(14,19; 2×1)`, 6 `(4,16; 3×1)`. Each trigger plays a sound and sets the player position to the start; none of these trigger scripts changes the home counter or game state. **Source-confirmed:** all six bounds and the two trigger actions. **Live test:** confirm each region is entered as a hazard, the sound/respawn work, and progress/HUD persist.

8. **HUD consistency.** At each repair and after a respawn, check the overlay counter against the number of powered homes (`0–5 / 5`) and that it remains visible/readable during movement. Scene and house scripts draw `HOMES %D0$01$ / 5`; house actors redraw it after their state changes. **Source-confirmed:** HUD text-draw events. **Live test:** confirm the dynamic value, placement, legibility and persistence on the actual browser display.

## Deferred sample-derived loop elements

- **Truck/substation intro:** no truck actor or scripted intro sequence is present in Storm Night. The scene begins with setup, music and controls help; the Substation is a static actor with “Grid starts here.” **Deferred.**
- **1/10 splice counter:** Storm Night uses the `Connected Houses` variable and a `HOMES … / 5` HUD, not a splice `1/10` counter. **Deferred.**
- **Free-form tether:** the five house scripts show/hide two fixed cable actors per house; no player-carried connector or free-form tether behavior is authored in these resources. **Deferred.**

## MCP source snapshot

Project `mr-cfe` was selected and read at revision `6cde9155a773210092b7267765f9e1be1c5167b367d002d31befd9d309eab44d`. MCP reported color mode `color`, default scene type `PLATFORM`, compiler preset `3000`, and start scene Storm Night at `(2,32)`. The five house gates are Marta `0`, Tomas `1`, Rosa `2`, Kiko `3`, Nuria `4`; music stages change at 2 and 4, with the final win branch at 5. The six hazard triggers all use the same sound-and-teleport actions. No build, emulator, or preview action was performed.
