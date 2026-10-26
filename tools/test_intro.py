"""Logo, intro story and title checks: python3 -m unittest discover -s tools -p test_intro.py (or cd tools).

Checks the contract in intro.py and the scenes, palettes and start setting that
make_intro_scene.py writes. Run the generator first; the file-level tests read
project/ as it is on disk.
"""
import json
import unittest
from pathlib import Path

import intro
import make_intro_scene as scene

PROJECT_DIR = scene.PROJECT_DIR
SCENES_DIR = PROJECT_DIR / "project" / "scenes"
PALETTE_DIR = PROJECT_DIR / "project" / "palettes"
SETTINGS_PATH = PROJECT_DIR / "project" / "settings.gbsres"
TOOLS_DIR = Path(__file__).resolve().parent
PLAYER = "player"
SCENE_FOLDERS = {intro.LOGO_SCENE_ID: "intro_logo",
                 intro.STORY_SCENE_ID: "intro_story",
                 intro.TITLE_SCENE_ID: "title"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def walk(events):
    for entry in events:
        yield entry
        for branch in entry.get("children", {}).values():
            yield from walk(branch)


def frames_of(entry) -> int:
    return entry["args"]["frames"]["value"]


def shot_wait_totals(script) -> list[int]:
    """Frames of EVENT_WAIT at the top level of the story script, per shot.

    A shot starts at its caption draw (overlay) and ends at the next one, or at
    the exit's EVENT_REMOVE_INPUT_SCRIPT for the last shot.
    """
    totals: list[int] = []
    for entry in script:
        command = entry["command"]
        if command == "EVENT_TEXT_DRAW" and entry["args"]["location"] == "overlay":
            totals.append(0)
        elif command == "EVENT_REMOVE_INPUT_SCRIPT":
            break
        elif command == "EVENT_WAIT" and totals:
            totals[-1] += frames_of(entry)
    return totals


def top_level_switches(events):
    return [e for e in events if e["command"] == "EVENT_SWITCH_SCENE"]


class ContractTests(unittest.TestCase):
    def test_captions_fit_the_box(self):
        self.assertEqual(intro.MAX_CAPTION_CHARS, 17)
        for name, lines, _ in intro.SHOTS:
            self.assertEqual(len(lines), 2, name)
            for line in lines:
                self.assertLessEqual(len(line), intro.MAX_CAPTION_CHARS, (name, line))

    def test_nine_shots_in_budget(self):
        self.assertEqual(len(intro.SHOTS), 9)
        for name, _, frames in intro.SHOTS:
            self.assertTrue(180 <= frames <= 240, (name, frames))

    def test_scanline_obj_peak_within_hardware_limit(self):
        self.assertLessEqual(intro._scanline_peak(intro.story_actors()), 10)

    def test_caption_generator_rejects_long_lines(self):
        with self.assertRaises(ValueError):
            scene.check_captions([("bad", ["x" * (intro.MAX_CAPTION_CHARS + 1)], 210)])

    def test_resource_ids_are_distinct(self):
        ids = {intro.LOGO_SCENE_ID, intro.STORY_SCENE_ID, intro.TITLE_SCENE_ID,
               *intro.BACKGROUND_IDS.values(), intro.RAIN_SPRITE_ID,
               intro.BOLT_SPRITE_ID, intro.POLE_SPRITE_ID}
        self.assertEqual(len(ids), 9)


class SceneFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenes = {}
        for scene_id, folder in SCENE_FOLDERS.items():
            cls.scenes[folder] = load(SCENES_DIR / folder / "scene.gbsres")

    def test_text_only_outside_logo_scenes(self):
        # EVENT_TEXT_DRAW in a LOGO scene corrupts background tiles (ROM a8e4f0ad).
        for scene_id, folder in SCENE_FOLDERS.items():
            draws = json.dumps(self.scenes[folder]).count("EVENT_TEXT_DRAW")
            if intro.SCENE_TYPES[scene_id] == "LOGO":
                self.assertEqual(draws, 0, folder)

    def test_three_logo_scenes_with_expected_ids(self):
        for scene_id, folder in SCENE_FOLDERS.items():
            data = self.scenes[folder]
            self.assertEqual(data["id"], scene_id, folder)
            self.assertEqual(data["type"], intro.SCENE_TYPES[scene_id], folder)
            self.assertEqual((data["width"], data["height"]), (intro.MAP_W, intro.MAP_H), folder)
            self.assertEqual(data["playerSpriteSheetId"], intro.HERO_SPRITE_ID, folder)
            self.assertEqual(data["autoFadeSpeed"], 1, folder)
            self.assertEqual(data["collisions"], scene.shared.collision_rle(
                scene.EMPTY_COLLISIONS, intro.MAP_W, intro.MAP_H), folder)

    def test_scene_indices_and_positions(self):
        for scene_id, folder, _, _, index, x, y in intro.SCENES:
            data = self.scenes[folder]
            self.assertEqual((data["_index"], data["x"], data["y"]), (index, x, y), folder)

    def test_backgrounds_and_palettes_reference_intro_ids(self):
        for _, folder, _, stem, _, _, _ in intro.SCENES:
            data = self.scenes[folder]
            self.assertEqual(data["backgroundId"], intro.BACKGROUND_IDS[stem], folder)
        expected = {
            "intro_logo": intro.LOGO_SLOTS,
            "intro_story": intro.STORY_SLOTS,
            "title": intro.TITLE_SLOTS,
        }
        for folder, slots in expected.items():
            self.assertEqual(self.scenes[folder]["paletteIds"],
                             [intro.palette_id(name) for name in slots], folder)
            self.assertEqual(slots[7], "ui", folder)

    def test_sprite_palette_slots(self):
        for folder in SCENE_FOLDERS.values():
            sprite_ids = self.scenes[folder]["spritePaletteIds"]
            self.assertEqual(len(sprite_ids), 8, folder)
            for name, slot in intro.SPRITE_SLOTS.items():
                self.assertEqual(sprite_ids[slot], intro.palette_id(name), (folder, name))

    def test_every_script_begins_by_hiding_the_player(self):
        for folder in SCENE_FOLDERS.values():
            first = self.scenes[folder]["script"][0]
            self.assertEqual(first["command"], "EVENT_ACTOR_HIDE", folder)
            self.assertEqual(first["args"]["actorId"], PLAYER, folder)

    def test_palette_files_exist_with_intro_ids(self):
        for name in intro.BG_PALETTES:
            data = load(PALETTE_DIR / f"intro_bg_{name}.gbsres")
            self.assertEqual(data["id"], intro.palette_id(name), name)
            self.assertEqual(data["colors"], intro.BG_PALETTES[name], name)
        for name, hardware in intro.SPRITE_PALETTES.items():
            data = load(PALETTE_DIR / f"intro_sprite_{name}.gbsres")
            self.assertEqual(data["id"], intro.palette_id(name), name)
            self.assertEqual(data["colors"], scene.shared.editor_sprite_colors(hardware), name)

    def test_story_actors_on_disk(self):
        actors = list((SCENES_DIR / "intro_story" / "actors").glob("*.gbsres"))
        expected = len(intro.RAIN) + len(intro.POLES) + 2   # + bolt and hero
        self.assertEqual(len(actors), expected)
        sprites = {load(path)["spriteSheetId"] for path in actors}
        self.assertEqual(sprites, {intro.RAIN_SPRITE_ID, intro.BOLT_SPRITE_ID,
                                   intro.POLE_SPRITE_ID, intro.HERO_SPRITE_ID})

    def test_event_and_resource_ids_are_unique(self):
        seen: set[str] = set()
        resources = [data for data in self.scenes.values()]
        for folder in SCENE_FOLDERS.values():
            for path in (SCENES_DIR / folder / "actors").glob("*.gbsres"):
                resources.append(load(path))
        for resource in resources:
            ids = [resource["id"]]
            for block in ("script", "startScript", "updateScript", "playerHit1Script"):
                ids.extend(entry["id"] for entry in walk(resource.get(block, [])))
            for identifier in ids:
                self.assertNotIn(identifier, seen, identifier)
                seen.add(identifier)


class StoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = load(SCENES_DIR / "intro_story" / "scene.gbsres")["script"]

    def test_both_story_exits_hide_the_caption_overlay(self):
        # Skip path and natural end each switch scenes; each must hide the overlay first.
        switches = hides = 0
        for e in walk(self.script):
            hides += e["command"] == "EVENT_OVERLAY_HIDE"
            switches += e["command"] == "EVENT_SWITCH_SCENE"
        self.assertEqual(hides, switches)
        self.assertEqual(switches, 2)

    def test_every_pole_snaps_and_every_thunder_plays(self):
        events = list(walk(self.script))
        snapped = {e["args"]["actorId"] for e in events
                   if e["command"] == "EVENT_ACTOR_SET_STATE"
                   and e["args"]["spriteStateId"] == "Snapped"}
        self.assertEqual(len(snapped), len(intro.POLES))
        crashes = sorted(e["args"]["duration"] for e in events
                         if e["command"] == "EVENT_SOUND_PLAY_EFFECT" and e["args"]["type"] == "crash")
        self.assertEqual(crashes, sorted(secs for _, _, secs in intro.THUNDER))

    def test_story_script_contains_every_caption(self):
        texts = [e["args"]["text"] for e in walk(self.script)
                 if e["command"] == "EVENT_TEXT_DRAW" and e["args"]["location"] == "overlay"]
        for name, lines, _ in intro.SHOTS:
            self.assertIn(intro.caption_text(lines), texts, name)
        self.assertEqual(len(texts), len(intro.SHOTS))
        for text in texts:
            for line in text.split("\n"):
                self.assertLessEqual(len(line), intro.MAX_CAPTION_CHARS)

    def test_caption_overlay_is_shown_once_at_its_position(self):
        shows = [e for e in walk(self.script) if e["command"] == "EVENT_OVERLAY_SHOW"]
        self.assertEqual(len(shows), 1)
        args = shows[0]["args"]
        self.assertEqual((args["x"], args["y"]), intro.CAPTION_OVERLAY)
        self.assertEqual(args["color"], intro.CAPTION_OVERLAY_COLOR)

    def test_start_script_hands_the_timeline_to_a_thread(self):
        # Scene start scripts are VM-locked; button scripts only fire once it ends.
        commands = [e["command"] for e in self.script]
        self.assertEqual(commands[-1], "EVENT_THREAD_START")
        self.assertNotIn("EVENT_WAIT", commands)

    def test_each_shot_waits_its_frame_budget(self):
        totals = shot_wait_totals(self.script[-1]["children"]["true"])
        self.assertEqual(totals, [frames for _, _, frames in intro.SHOTS])

    def test_skip_and_exit_both_go_to_title(self):
        targets = [e for e in walk(self.script) if e["command"] == "EVENT_SWITCH_SCENE"]
        self.assertTrue(targets)
        for entry in targets:
            self.assertEqual(entry["args"]["sceneId"], intro.TITLE_SCENE_ID)

    def test_skip_input_set_on_a_and_start(self):
        inputs = [e for e in self.script if e["command"] == "EVENT_SET_INPUT_SCRIPT"]
        self.assertEqual(len(inputs), 1)
        self.assertEqual(inputs[0]["args"]["input"], ["a", "start"])
        self.assertIs(inputs[0]["args"]["override"], True)

    def test_hero_walks_to_its_stop(self):
        moves = [e for e in walk(self.script) if e["command"] == "EVENT_ACTOR_MOVE_TO"]
        self.assertEqual(len(moves), 1)
        args = moves[0]["args"]
        self.assertEqual((args["x"]["value"], args["y"]["value"]),
                         intro.HERO_STOP)
        self.assertEqual(args["collideWith"], [])


class TitleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = load(SCENES_DIR / "title" / "scene.gbsres")["script"]

    def test_title_switches_to_opening_at_start_position(self):
        start_inputs = [e for e in self.script
                        if e["command"] == "EVENT_SET_INPUT_SCRIPT"
                        and e["args"]["input"] == ["start"]]
        self.assertEqual(len(start_inputs), 1)
        switches = top_level_switches(walk(start_inputs[0]["children"]["true"]))
        self.assertEqual(len(switches), 1)
        args = switches[0]["args"]
        self.assertEqual(args["sceneId"], intro.OPENING_SCENE_ID)
        self.assertEqual((args["x"]["value"], args["y"]["value"]), (1, 15))
        self.assertEqual(args["direction"], "right")
        self.assertEqual(args["fadeSpeed"], intro.FADE_SPEED)

    def test_title_switch_targets_opening_scene_file(self):
        opening_scene = load(SCENES_DIR / "service_opening" / "scene.gbsres")
        self.assertEqual(opening_scene["id"], intro.OPENING_SCENE_ID)

    def test_title_starts_with_overlay_hidden(self):
        commands = [e["command"] for e in self.script[:3]]
        self.assertIn("EVENT_OVERLAY_HIDE", commands)

    def test_title_draws_no_runtime_text(self):
        # Text draws garbled the title (ROMs 7f850ff5, 8125c692); it is baked art.
        self.assertNotIn("EVENT_TEXT_DRAW", json.dumps(self.script))

    def test_press_start_blinks_by_palette_swap(self):
        self.assertEqual(self.script[-1]["command"], "EVENT_THREAD_START")
        loops = [e for e in walk(self.script) if e["command"] == "EVENT_LOOP"]
        self.assertEqual(len(loops), 1)
        body = loops[0]["children"]["true"]
        swaps = [e["args"][f"palette{intro.PRESS_SLOT}"] for e in body
                 if e["command"] == "EVENT_PALETTE_SET_BACKGROUND"]
        self.assertEqual(swaps, [intro.palette_id("ui"), intro.palette_id("press_off")])
        waits = [frames_of(e) for e in body if e["command"] == "EVENT_WAIT"]
        self.assertEqual(waits, [intro.BLINK_FRAMES, intro.BLINK_FRAMES])


class LogoTests(unittest.TestCase):
    def test_logo_holds_then_moves_to_story(self):
        script = load(SCENES_DIR / "intro_logo" / "scene.gbsres")["script"]
        waits = [frames_of(e) for e in script if e["command"] == "EVENT_WAIT"]
        self.assertEqual(waits, [intro.LOGO_HOLD_FRAMES])
        switches = top_level_switches(script)
        self.assertEqual(len(switches), 1)
        self.assertEqual(switches[0]["args"]["sceneId"], intro.STORY_SCENE_ID)


class MusicAndVoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.logo = load(SCENES_DIR / "intro_logo" / "scene.gbsres")["script"]
        cls.title = load(SCENES_DIR / "title" / "scene.gbsres")["script"]

    def test_theme_files_exist_with_contract_ids(self):
        music = TOOLS_DIR.parent / "assets" / "music"
        for key in intro.THEMES:
            name = intro.THEME_FILES[key]
            self.assertTrue((music / f"{name}.uge").stat().st_size > 0, name)
            self.assertEqual(load(music / f"{name}.uge.gbsres")["id"], intro.THEME_IDS[key])

    def test_logo_sets_the_voice_and_starts_the_default_theme(self):
        commands = {e["command"]: e["args"] for e in self.logo}
        self.assertEqual(commands["EVENT_TEXT_SET_SOUND_EFFECT"], intro.TEXT_SOUND)
        self.assertEqual(commands["EVENT_MUSIC_PLAY"]["musicId"],
                         intro.THEME_IDS[intro.DEFAULT_THEME])
        order = [e["command"] for e in self.logo]
        self.assertLess(order.index("EVENT_MUSIC_PLAY"), order.index("EVENT_SWITCH_SCENE"))

    def test_select_on_the_title_auditions_every_theme(self):
        played = {e["args"]["musicId"] for e in walk(self.title)
                  if e["command"] == "EVENT_MUSIC_PLAY"}
        if intro.AUDITION_THEMES:
            self.assertEqual(played, set(intro.THEME_IDS.values()))
        else:
            self.assertEqual(played, set())


class SettingsTests(unittest.TestCase):
    def test_start_scene_is_the_logo(self):
        data = load(SETTINGS_PATH)
        self.assertEqual(data["startSceneId"], intro.LOGO_SCENE_ID)
        self.assertEqual((data["startX"], data["startY"], data["startDirection"]),
                         (0, 0, "right"))

    def test_no_other_generator_owns_the_start_scene(self):
        allowed = {"make_intro_scene.py", "make_scene.py"}
        owners = []
        for path in sorted(TOOLS_DIR.glob("make_*.py")):
            if path.name in allowed:
                continue
            text = path.read_text(encoding="utf-8")
            if "settings.gbsres" in text or "startSceneId" in text:
                owners.append(path.name)
        self.assertEqual(owners, [])

    def test_generator_output_is_deterministic(self):
        first = scene.build_scenes()
        second = scene.build_scenes()
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(scene.settings_update(None), scene.settings_update(None))

    def test_settings_keys_outside_the_intro_are_untouched(self):
        before = load(SETTINGS_PATH)
        updated = scene.settings_update(None)
        changed = {k for k in before if before[k] != updated.get(k)}
        self.assertLessEqual(changed, set(intro.settings_start()))


if __name__ == "__main__":
    unittest.main()
