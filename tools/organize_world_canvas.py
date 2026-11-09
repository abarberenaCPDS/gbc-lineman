"""Apply the registry's editor-only layout, finding editor-renamed scenes by ID.

Opening flow is the first row, then one row per household in mission order;
labs and legacy references sit below production. Gameplay coordinates stay intact.
"""
import json
from pathlib import Path
import scenes


def main():
    entries = {entry['id']: entry for entry in scenes.REGISTRY.values()}
    count = 0
    for path in scenes.SCENES_DIR.glob('*/scene.gbsres'):
        data = json.loads(path.read_text())
        entry = entries.get(data['id'])
        if entry is None:
            raise ValueError(f'Unregistered scene: {path}')
        data['x'], data['y'] = entry['editor']
        path.write_text(json.dumps(data, indent=2) + '\n')
        count += 1
    print(f'Organized {count} scenes; gameplay geometry unchanged.')


if __name__ == '__main__':
    main()
