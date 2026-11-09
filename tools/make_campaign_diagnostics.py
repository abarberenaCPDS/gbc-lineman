#!/usr/bin/env python3
"""Generate isolated seeded campaign diagnostics under build/diagnostics.

Never changes production resources or launch settings. These fixtures are not
an uninterrupted campaign playtest. Build each selected copy through MCP.
"""
import json
from pathlib import Path
import shutil
import uuid
import make_intro_scene as launch

ROOT = Path(__file__).resolve().parent.parent


def event(command, args, key):
    """Create a diagnostic event with a reproducible resource ID."""
    return {
        'command': command,
        'args': args,
        'id': str(uuid.uuid5(uuid.NAMESPACE_URL, 'campaign-diagnostic:' + key)),
    }


def seed(values):
    """Set fixture globals before the selected scene's normal init script."""
    return [
        event('EVENT_SET_VALUE', {
            'variable': variable, 'value': {'type': 'number', 'value': value},
        }, variable)
        for variable, value in values.items()
    ]


def seed_once(values):
    """Initialize a route fixture once; preserve earned state on scene returns."""
    import make_ticket_scene as ticket
    if '56' in values:
        raise ValueError('variable 56 is reserved for diagnostic initialization')
    initialized = event('EVENT_SET_VALUE', {
        'variable': '56', 'value': {'type': 'number', 'value': 1},
    }, 'route-fixture-initialized')
    return [ticket.if_value('56', 0, 'route-fixture-first-entry', [*seed(values), initialized])]


def fixture(name, folder, x, y, values, *, seed_once_only=False):
    """Copy production inputs, seed one scene, and delegate the test start."""
    destination = ROOT / 'build/diagnostics' / name
    destination.mkdir(parents=True, exist_ok=True)
    for resource_folder in ('assets', 'project'):
        shutil.copytree(ROOT / resource_folder, destination / resource_folder, dirs_exist_ok=True)
    shutil.copy2(ROOT / 'mr-cfe.gbsproj', destination / 'mr-cfe.gbsproj')
    scene_path = destination / 'project/scenes' / folder / 'scene.gbsres'
    scene = json.loads(scene_path.read_text())
    scene['script'] = (seed_once(values) if seed_once_only else seed(values)) + scene['script']
    scene_path.write_text(json.dumps(scene, indent=2) + '\n')
    original_settings = launch.SETTINGS_PATH
    try:
        launch.SETTINGS_PATH = destination / original_settings.relative_to(ROOT)
        launch.write_settings((scene['id'], x, y, 'right'))
    finally:
        launch.SETTINGS_PATH = original_settings
    return destination


def main():
    """Generate the board, fresh-campaign and street-reentry diagnostic copies."""
    board = fixture('board', 'storm_climb', 11, 17, {'16': 0, '40': 1, '41': 1, '44': 2, '6': 3, '50': 1, '51': 1})
    # Keep only board 2 active so other hazards cannot confound the escape inputs.
    for actor_path in (board / 'project/scenes/storm_climb/actors').glob('*.gbsres'):
        actor = json.loads(actor_path.read_text())
        if actor.get('collisionGroup') == '1' and actor.get('symbol') != 'board_02':
            actor.update(collisionGroup='', updateScript=[], startScript=[])
            actor_path.write_text(json.dumps(actor, indent=2) + '\n')
    registered = json.loads((ROOT / 'project/variables.gbsres').read_text())['variables']
    values = {variable['id']: 1 for variable in registered if variable['id'] not in ('14',)}
    values.update({'44': 5, '6': 5, '16': 4, '14': 2})
    fixture('new-run', 'title', 0, 0, values)
    fixture('reentry', 'service_opening', 16, 9, {'4': 1, '54': 1, '44': 0, '16': 0, '6': 0})
    print('Generated isolated board, new-run and reentry diagnostic copies; production launch unchanged.')

if __name__ == '__main__':
    main()
