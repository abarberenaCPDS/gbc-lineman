"""Engine field overrides (stdlib only)."""

from __future__ import annotations

import json
import unittest

import make_engine_fields as fields


class EngineFieldTests(unittest.TestCase):
    def test_drop_through_is_a_tap_not_a_hold(self):
        # B-07: hold mode fell through every one-way shelf while Down+A was held.
        data = json.loads(fields.ENGINE_FIELDS_PATH.read_text(encoding="utf-8"))
        values = {f["id"]: f["value"] for f in data["engineFieldValues"]}
        self.assertEqual(values["FEAT_PLATFORM_DROP_THROUGH"], 1)
        self.assertEqual(values["INPUT_PLATFORM_DROP_THROUGH"], "DROP_THRU_INPUT_DOWN_JUMP_TAP")


if __name__ == "__main__":
    unittest.main()
