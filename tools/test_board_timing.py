"""Execute generated board events against timed player positions (no emulator)."""
import unittest

import climb  # initialize the route contract before hazards
import hazards


def event(command, args, key):
    return {"command": command, "args": args, "id": key}


def wait(frames, key):
    return event("EVENT_WAIT", {"frames": {"type": "number", "value": frames}}, key)


def set_value(variable, value, key):
    return event("EVENT_SET_VALUE", {"variable": variable, "value": {"type": "number", "value": value}}, key)


def if_value(variable, value, key, yes, no=None):
    node = event("EVENT_IF", {"condition": {"type": "eq", "valueA": {"type": "variable", "value": variable},
                                            "valueB": {"type": "number", "value": value}}}, key)
    node["children"] = {"true": yes, "false": no or []}
    return node


class BoardVM:
    """Small interpreter for the real generated event subset; waits yield frames."""
    def __init__(self, number=2, board=(15, 9, 11)):
        self.number = number
        self.actor_id = "board-owner"
        self.values = {"15": number}  # scene-init loop may already see body overlap
        self.x, self.y = 9 * 8, 17 * 8
        self.frame = 0
        self.updates = 0
        self.breaks = []
        self.first_contacts = []
        self.position_reads = []
        self.vertical_reads = []
        self.state = "Idle"
        self.executed = {}
        self.script = hazards.board_update_script(number, f"board:{number}", event, wait, if_value, set_value,
                                                  board, hide_idle=True)
        self.runner = self.loop()
        list(self.execute(hazards.board_start_script(f"board:{number}", event)))

    def value(self, item):
        kind = item["type"]
        if kind == "number": return item["value"]
        if kind == "variable": return self.values.get(item["value"], 0)
        if kind == "property":
            self.assert_player_property(item)
            return self.x if item["property"] == "pxpos" else self.y
        a, b = self.value(item["valueA"]), self.value(item["valueB"])
        return {"add": lambda: a+b, "eq": lambda: a==b, "gte": lambda: a>=b,
                "lte": lambda: a<=b, "and": lambda: a and b}[kind]()

    @staticmethod
    def assert_player_property(item):
        if item["target"] != "player" or item["property"] not in {"pxpos", "pypos"}:
            raise AssertionError(item)

    def property_fetch(self, condition):
        def properties(item):
            if item["type"] == "property": yield item
            for field in ("valueA", "valueB"):
                if field in item: yield from properties(item[field])
        found = list(properties(condition))
        if found:
            # Native compiler deduplicates actor-position fetches within a
            # condition, including the two horizontal-bound comparisons.
            self.executed["POSITION_FETCH"] = self.executed.get("POSITION_FETCH", 0) + 1
            self.position_reads.append(self.frame)
            if any(p["property"] == "pypos" for p in found): self.vertical_reads.append(self.frame)

    def execute(self, script):
        for node in script:
            command, args = node["command"], node["args"]
            self.executed[command] = self.executed.get(command, 0) + 1
            if command == "EVENT_SET_VALUE": self.values[args["variable"]] = self.value(args["value"])
            elif command == "EVENT_IF":
                self.property_fetch(args["condition"])
                yield from self.execute(node["children"]["true" if self.value(args["condition"]) else "false"])
            elif command == "EVENT_WAIT":
                for _ in range(self.value(args["frames"])): yield
            elif command == "EVENT_ACTOR_SET_STATE":
                self.state = args["spriteStateId"]
                if self.state == "Creak": self.first_contacts.append(self.frame)
            elif command == "EVENT_ACTOR_COLLISIONS_ENABLE": self.breaks.append(self.frame)
            elif command == "EVENT_ACTOR_STOP_UPDATE":
                if args["actorId"] != self.actor_id: raise AssertionError(args)
                self.runner = None
            elif command == "EVENT_ACTOR_START_UPDATE":
                if args["actorId"] != self.actor_id: raise AssertionError(args)
                self.runner = self.loop()
            elif command not in {"EVENT_ACTOR_COLLISIONS_DISABLE", "EVENT_ACTOR_SHOW", "EVENT_ACTOR_HIDE"}:
                raise AssertionError(command)

    def loop(self):
        while True:
            self.updates += 1
            yield from self.execute(self.script)
            # GB Studio compileEntityEvents appends VM_IDLE and a loop jump
            # to every actor update script, even if it has no authored WAIT.
            yield

    def advance(self, frames, x=None, y=None):
        if x is not None: self.x = x
        if y is not None: self.y = y
        for _ in range(frames):
            if self.runner is not None: next(self.runner)
            self.frame += 1



    def trigger(self, entering):
        enter, leave = hazards.board_trigger_scripts(self.number, "board:trigger", set_value,
                                                     event, self.actor_id, hide_idle=True)
        list(self.execute(enter if entering else leave))


class BoardTimingTests(unittest.TestCase):
    def test_body_overlap_below_board_never_starts_warning(self):
        vm = BoardVM()
        vm.advance(150, y=17*8)
        self.assertEqual(vm.state, "Idle")
        self.assertEqual(vm.first_contacts, [])
        self.assertEqual(vm.breaks, [])
        vm.advance(hazards.CREAK_FRAMES, y=14*8)
        self.assertEqual(vm.breaks, [])
        vm.advance(4)
        self.assertEqual(vm.breaks[-1] - vm.first_contacts[-1], hazards.CREAK_FRAMES)
        self.assertTrue(150 <= vm.first_contacts[-1] <= 153)

    def test_continuous_contact_uses_one_native_wait_not_recurring_polls(self):
        vm = BoardVM()
        vm.advance(hazards.CREAK_FRAMES, y=14*8)
        self.assertEqual(vm.breaks, [])
        self.assertEqual(vm.position_reads, [0])
        vm.advance(1)
        self.assertEqual(vm.breaks, [50])
        self.assertEqual(vm.position_reads, [0, 50])

    def test_leave_cancels_pending_warning_and_restores_idle_immediately(self):
        vm = BoardVM()
        vm.advance(30, y=14*8)
        self.assertEqual(vm.state, "Creak")
        vm.trigger(False)
        self.assertEqual(vm.values[hazards.VAR_ON_BOARD], 0)
        self.assertEqual(vm.state, "Idle")
        self.assertIsNone(vm.runner)
        reads = list(vm.position_reads)
        vm.advance(100)
        self.assertEqual(vm.breaks, [])
        self.assertEqual(vm.position_reads, reads)

    def test_one_frame_body_leave_reentry_gets_a_fresh_full_warning(self):
        vm = BoardVM()
        vm.advance(30, y=14*8)
        vm.trigger(False)
        vm.advance(1, y=14*8-8)
        vm.trigger(True)
        vm.advance(hazards.CREAK_FRAMES, y=14*8)
        self.assertEqual(vm.breaks, [])
        vm.advance(1)
        self.assertEqual(vm.first_contacts, [0, 31])
        self.assertEqual(vm.breaks, [81])

    def test_same_trigger_restart_does_not_resume_old_wait(self):
        vm = BoardVM()
        vm.advance(30, y=14*8)
        vm.trigger(True)
        self.assertEqual(vm.state, "Idle")
        vm.advance(hazards.CREAK_FRAMES)
        self.assertEqual(vm.breaks, [])
        vm.advance(1)
        self.assertEqual(vm.breaks, [80])

    def test_stale_flag_after_horizontal_teleport_cannot_hit_or_rearm(self):
        vm = BoardVM()
        vm.advance(30, y=14*8)
        vm.advance(90, x=12*8)  # no leave event: deadline must reject the stale flag
        self.assertEqual(vm.breaks, [])
        self.assertEqual(vm.first_contacts, [0])
        self.assertEqual(vm.state, "Idle")

    def test_stale_flag_after_vertical_teleport_cannot_hit(self):
        vm = BoardVM()
        vm.advance(30, y=14*8)
        vm.advance(90, y=17*8)
        self.assertEqual(vm.breaks, [])
        self.assertEqual(vm.first_contacts, [0])

    def test_respawn_clears_flag_so_old_deadline_cannot_hit(self):
        vm = BoardVM()
        vm.advance(30, y=14*8)
        vm.values[hazards.VAR_ON_BOARD] = 0  # scene-specific respawn already does this
        vm.advance(90)
        self.assertEqual(vm.breaks, [])
        self.assertEqual(vm.state, "Idle")

    def test_stopped_board_can_restart_when_culling_reactivates_it(self):
        vm = BoardVM()
        vm.trigger(False)
        vm.runner = vm.loop()  # engine activation restarts the owner update
        vm.advance(120, y=14*8)
        self.assertEqual(vm.breaks, [])
        self.assertEqual(vm.position_reads, [])
        vm.trigger(True)
        vm.advance(51)
        self.assertEqual(vm.breaks, [170])

    def test_distant_boards_keep_old_idle_cadence_without_position_reads(self):
        vm = BoardVM()
        vm.values[hazards.VAR_ON_BOARD] = 0
        vm.advance(120)
        self.assertEqual(vm.executed.get("POSITION_FETCH", 0), 0)
        self.assertEqual(vm.updates, 60)
        self.assertEqual(vm.breaks, [])

    def test_visible_and_background_boards_reset_with_matching_visibility(self):
        for hidden in (False, True):
            with self.subTest(hidden=hidden):
                enter, leave = hazards.board_trigger_scripts(2, "b", set_value, event, "owner", hide_idle=hidden)
                self.assertEqual(enter[0]["args"]["variable"], hazards.VAR_ON_BOARD)
                self.assertEqual(enter[-1]["command"], "EVENT_ACTOR_START_UPDATE")
                self.assertEqual(enter[1]["command"], "EVENT_ACTOR_STOP_UPDATE")
                self.assertEqual(leave[1]["command"], "EVENT_ACTOR_STOP_UPDATE")
                self.assertNotIn("EVENT_ACTOR_START_UPDATE", [e["command"] for e in leave])
                self.assertEqual("EVENT_ACTOR_HIDE" in [e["command"] for e in enter], hidden)
                self.assertEqual("EVENT_ACTOR_HIDE" in [e["command"] for e in leave], hidden)

    def test_generated_event_ids_are_unique_across_update_start_and_triggers(self):
        def walk(nodes):
            for node in nodes:
                yield node
                for children in node.get("children", {}).values(): yield from walk(children)
        vm = BoardVM()
        enter, leave = hazards.board_trigger_scripts(2, "board:trigger", set_value, event, vm.actor_id, hide_idle=True)
        nodes = [*vm.script, *hazards.board_start_script("board:2", event), *enter, *leave]
        ids = [node["id"] for node in walk(nodes)]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__": unittest.main()
