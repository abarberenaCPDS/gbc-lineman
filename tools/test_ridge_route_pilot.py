"""Isolation and native-resource checks for the optional 64x36 route fixture."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / 'build/diagnostics/ridge-route-pilot'


def source_hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('assets', 'project') for p in (ROOT / folder).rglob('*')
            if p.is_file()}


def events(value):
    if isinstance(value, dict):
        if 'command' in value:
            yield value
        for child in value.values():
            yield from events(child)
    elif isinstance(value, list):
        for child in value:
            yield from events(child)


class RidgeRoutePilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = source_hashes()
        subprocess.run([sys.executable, str(ROOT / 'tools/make_ridge_route_pilot.py')],
                       check=True, capture_output=True, text=True)
        cls.after = source_hashes()
        cls.scene = json.loads((FIXTURE / 'project/scenes/wind_ridge/scene.gbsres').read_text())
        cls.manifest = json.loads((FIXTURE / 'route-pilot.json').read_text())

    def test_generation_keeps_production_and_other_scenes_identical(self):
        self.assertEqual(self.before, self.after)
        for path in (ROOT / 'project/scenes').rglob('*.gbsres'):
            if path.relative_to(ROOT / 'project/scenes').parts[0] in ('wind_ridge', 'ridge_saddle'):
                continue
            self.assertEqual(path.read_bytes(), (FIXTURE / path.relative_to(ROOT)).read_bytes(), str(path))

    def test_both_scenes_have_headroom_and_safe_terraces(self):
        self.assertEqual((self.scene['width'], self.scene['height']), (64, 36))
        saddle = json.loads((FIXTURE / 'project/scenes/ridge_saddle/scene.gbsres').read_text())
        self.assertEqual((saddle['width'], saddle['height']), (64, 36))
        terraces = self.manifest['terraces']
        for a, b in zip(terraces, terraces[1:]):
            self.assertEqual(a[1] + 1, b[0], 'no deep pocket between terraces')
            self.assertEqual(a[2] - b[2], 3, 'short-step route remains available')

    def test_reentry_does_not_repeat_fresh_job_seed(self):
        first = self.scene['script'][0]
        self.assertEqual(first['command'], 'EVENT_IF')
        condition = first['args']['condition']
        self.assertEqual(condition['type'], 'eq')
        self.assertEqual(condition['valueA'], {'type': 'variable', 'value': '55'})
        self.assertEqual(condition['valueB'], {'type': 'number', 'value': 0})
        top_level_ticket_seeds = [e for e in self.scene['script'] if e['command'] == 'EVENT_SET_VALUE'
                                 and e.get('args', {}).get('variable') == '16']
        self.assertEqual(top_level_ticket_seeds, [])
        variables = json.loads((FIXTURE / 'project/variables.gbsres').read_text())['variables']
        self.assertEqual(sum(v['id'] == '55' for v in variables), 1)

    def test_relocated_checkpoints_and_return_entry(self):
        positions = [(e['args'].get('x'), e['args'].get('y')) for e in events(self.scene['playerHit1Script'])
                     if e['command'] == 'EVENT_ACTOR_SET_POSITION']
        # Native number fields are expressions, not bare coordinate numbers.
        numbers = {(p[0].get('value'), p[1].get('value')) for p in positions if isinstance(p[0], dict)}
        self.assertTrue({(2, 32), (18, 26), (38, 17)} <= numbers, numbers)
        self.assertEqual(self.manifest['lines'][2]['pole'], [40, 17])
        self.assertEqual(self.manifest['lines'][2]['box_scene'], 'ridge_saddle')
        self.assertEqual(self.manifest['terraces'][-1][:3], [42, 62, 15])
        self.assertIn([56, 14], self.manifest['layouts']['wind_ridge']['entries'])
        self.assertIn([2, 26], self.manifest['layouts']['ridge_saddle']['entries'])


    def test_arches_leave_jump_clearance_at_the_exit(self):
        roofs = self.manifest['roofs']
        # A 24px actor in a four-row passage can hop, but cannot clear a full
        # chest-level gust band. Roof ends before the next riser so it cannot trap him.
        for folder, floor, next_riser in [('wind_ridge', 21, 36), ('ridge_saddle', 33, 54)]:
            x0, x1, top, underside = roofs[folder]
            self.assertEqual(floor - underside - 1, 4)
            self.assertEqual(top, 2, 'no reachable upper bypass above the arch')
            self.assertGreaterEqual(next_riser - x1 - 1, 3)
        self.assertEqual(self.manifest['lines'][4]['pole'], [37, 32])
        self.assertEqual(self.manifest['lines'][4]['checkpoint'], [56, 29])


    def test_saddle_waiting_area_fits_body_and_release_drift(self):
        lanes = self.manifest['layouts']['ridge_saddle']['hazards']
        arc = next(lane for lane in lanes if lane[0] == 'arc')
        gust = next(lane for lane in lanes if lane[0] == 'gust' and lane[1] == 31)
        # Hero bounds are x+2..x+13 inclusive. Source intervals here deliberately
        # include the failed native wait at363px plus the measured23px release.
        safe_min = (arc[3]+1)*8 - 2
        safe_max = gust[2]*8 - 14
        self.assertGreaterEqual(safe_max-safe_min, 36)
        self.assertLessEqual(safe_min, 363)
        self.assertGreaterEqual(safe_max, 363)
        self.assertLessEqual(352+23, safe_max)
        self.assertGreaterEqual(368-23, safe_min)
        self.assertEqual(self.manifest['lines'][4]['box'], [54, 29])
        self.assertEqual(self.manifest['revision'], 3)

    def test_cross_scene_destinations_match_shifted_entries(self):
        for folder, target, expected in [('wind_ridge','ridge_saddle',(2,26)),
                                          ('ridge_saddle','wind_ridge',(56,14))]:
            target_scene = json.loads((FIXTURE / f'project/scenes/{target}/scene.gbsres').read_text())
            switches = []
            for path in (FIXTURE / f'project/scenes/{folder}/triggers').glob('*.gbsres'):
                switches += [e for e in events(json.loads(path.read_text()))
                             if e['command'] == 'EVENT_SWITCH_SCENE'
                             and e['args'].get('sceneId') == target_scene['id']]
            self.assertEqual(len(switches), 1)
            args = switches[0]['args']
            def number(v):
                return v['value'] if isinstance(v, dict) else v
            self.assertEqual((number(args['x']), number(args['y'])), expected)

    def test_static_route_rules_pass_for_both_copied_layouts(self):
        code = "import sys,json;sys.path.insert(0,'tools');import make_ridge_route_pilot as p,test_routes,ridge;p.configure_contract();print(json.dumps({f:test_routes.problems(c.route_scene()) for f,c in ridge.LAYOUTS.items()}))"
        result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, check=True,
                                capture_output=True, text=True)
        issues = json.loads(result.stdout)
        self.assertTrue(all(not failures for groups in issues.values() for failures in groups.values()), issues)


if __name__ == '__main__':
    unittest.main()
