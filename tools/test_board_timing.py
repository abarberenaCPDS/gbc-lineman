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
        self.values = {"15": number}  # body trigger is intentionally always armed
        self.x, self.y = 9 * 8, 17 * 8
        self.frame = 0
        self.breaks = []
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
        a, b = self.value(item["valueA"]), self.value(item["valueB"])
        return {"add": lambda: a+b, "eq": lambda: a==b, "gte": lambda: a>=b,
                "lte": lambda: a<=b, "and": lambda: a and b}[kind]()

    def execute(self, script):
        for node in script:
            command, args = node["command"], node["args"]
            self.executed[command] = self.executed.get(command, 0) + 1
            if command == "EVENT_ACTOR_GET_POSITION":
                self.values[args["vectorX"]], self.values[args["vectorY"]] = self.x, self.y
            elif command == "EVENT_SET_VALUE": self.values[args["variable"]] = self.value(args["value"])
            elif command == "EVENT_IF":
                yield from self.execute(node["children"]["true" if self.value(args["condition"]) else "false"])
            elif command == "EVENT_WAIT":
                for _ in range(self.value(args["frames"])): yield
            elif command == "EVENT_ACTOR_SET_STATE": self.state = args["spriteStateId"]
            elif command == "EVENT_ACTOR_COLLISIONS_ENABLE": self.breaks.append(self.frame)
            elif command not in {"EVENT_ACTOR_COLLISIONS_DISABLE", "EVENT_ACTOR_SHOW", "EVENT_ACTOR_HIDE"}:
                raise AssertionError(command)

    def loop(self):
        while True:
            yield from self.execute(self.script)
            # GB Studio compileEntityEvents appends VM_IDLE and a loop jump
            # to every actor update script, even if it has no authored WAIT.
            yield

    def advance(self, frames, x=None, y=None):
        if x is not None: self.x = x
        if y is not None: self.y = y
        for _ in range(frames):
            next(self.runner)
            self.frame += 1


class BoardTimingTests(unittest.TestCase):
    def test_body_overlap_from_lower_shelf_never_starts_countdown(self):
        vm = BoardVM()
        vm.advance(150, y=17*8)  # head touches board-2 trigger at row14
        self.assertEqual(vm.values[hazards.BOARD_LOCAL_TIMER], 0)
        self.assertEqual(vm.state, "Idle")
        self.assertEqual(vm.breaks, [])
        vm.advance(hazards.CREAK_FRAMES, y=14*8)
        self.assertEqual(vm.breaks, [])
        vm.advance(1)
        self.assertEqual(vm.breaks, [150 + hazards.CREAK_FRAMES])

    def test_jumping_away_restarts_full_warning_on_return(self):
        vm = BoardVM()
        vm.advance(30, y=14*8)
        vm.advance(1, y=14*8-1)
        self.assertEqual(vm.values[hazards.BOARD_LOCAL_TIMER], 0)
        vm.advance(hazards.CREAK_FRAMES, y=14*8)
        self.assertEqual(vm.breaks, [])
        vm.advance(1)
        self.assertEqual(vm.breaks, [31 + hazards.CREAK_FRAMES])

    def test_walking_off_resets_even_when_trigger_flag_is_stale(self):
        vm = BoardVM()
        vm.advance(30, y=14*8)
        vm.advance(90, x=12*8, y=14*8)  # left bound 98 is beyond board end95
        self.assertEqual(vm.values[hazards.BOARD_LOCAL_TIMER], 0)
        self.assertEqual(vm.breaks, [])

    def test_crossing_foot_height_in_air_does_not_accumulate(self):
        vm = BoardVM()
        for _ in range(80):
            vm.advance(1, y=14*8)
            vm.advance(1, y=14*8-1)
        self.assertEqual(vm.breaks, [])

    def test_boards_keep_independent_actor_local_timers(self):
        a, b = BoardVM(), BoardVM(number=3, board=(6, 13, 15))
        for _ in range(51):
            a.advance(1, y=14*8)
            b.advance(1, y=14*8)
        self.assertEqual(a.breaks, [50])
        self.assertEqual(b.breaks, [])
        self.assertEqual(b.values[hazards.BOARD_LOCAL_TIMER], 0)

    def test_idle_boards_do_not_repeat_animation_or_collision_changes(self):
        vm = BoardVM()
        states = vm.executed.get("EVENT_ACTOR_SET_STATE", 0)
        disables = vm.executed.get("EVENT_ACTOR_COLLISIONS_DISABLE", 0)
        vm.advance(100)
        self.assertEqual(vm.executed.get("EVENT_ACTOR_SET_STATE", 0), states)
        self.assertEqual(vm.executed.get("EVENT_ACTOR_COLLISIONS_DISABLE", 0), disables)

    def test_generated_event_ids_are_unique_within_each_board(self):
        def walk(nodes):
            for node in nodes:
                yield node
                for children in node.get("children", {}).values(): yield from walk(children)
        vm = BoardVM()
        ids = [node["id"] for node in walk(vm.script)]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__": unittest.main()
