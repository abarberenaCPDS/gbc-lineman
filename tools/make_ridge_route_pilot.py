#!/usr/bin/env python3
"""Generate isolated revision-3 Ridge route fixtures; production stays intact.

Both copied ridge scenes use 64x36 framing. The production generators and assets
remain authoritative; this process-local contract changes terrain and placement,
never physics or collision bounds. Use managed Pillow Python; main owns runtime.
"""
from __future__ import annotations
import argparse
import copy
from dataclasses import replace
import json
from pathlib import Path
import ridge
import grid_chain
import scene_links
import make_campaign_diagnostics as diagnostics

ROOT = Path(__file__).resolve().parent.parent
START = (2, 32)
SADDLE_SHIFT = 18
TERRACES = [(15, 22, 27, 32), (23, 28, 24, 32), (29, 35, 21, 32),
            (36, 41, 18, 32), (42, 62, 15, 32)]
WIND_ROOF = (29, 32, 2, 16)
SADDLE_ROOF = (40, 49, 2, 28)


def configure_contract():
    """Patch imported contracts only in this generator process."""
    saddle = copy.deepcopy(ridge.SADDLE_LAYOUT)
    ridge.MAP_H, ridge.GROUND_ROW = 36, 33
    ridge.START = START
    ridge.LINES = copy.deepcopy(ridge.LINES)
    ridge.LINES[0].update(pole=(6, 29), box=(16, 26), checkpoint=(18, 26))
    ridge.LINES[1].update(pole=(20, 26), box=(36, 17), checkpoint=(38, 17))
    # This rejected pilot is a historical fixture. Keep its original approach
    # and pads explicit so the production lakeside redesign cannot move them.
    ridge.LINES[2].update(pole=(40, 17), box=(14, 11), checkpoint=(16, 11))
    ridge.LINES[3].update(pole=(18, 11), box=(33, 11), checkpoint=(35, 11))
    ridge.LINES[3].pop("reach", None)
    ridge.LINES[4].update(pole=(37, 14), box=(54, 11), checkpoint=(56, 11))
    for line in ridge.LINES:
        for field in ('pole', 'box', 'checkpoint'):
            owner = line['pole_scene' if field == 'pole' else 'box_scene']
            if owner == ridge.SADDLE and field in line:
                x, y = line[field]
                line[field] = (x, y + SADDLE_SHIFT)
    # The porch and its completion effects move together with the framing.
    for name in ('TOMAS', 'CONCENTRATOR', 'HOUSE_DOOR'):
        x, y = getattr(ridge, name)
        setattr(ridge, name, (x, y + SADDLE_SHIFT))
    x0, x1, y0, y1 = ridge.HOUSE_RECT
    ridge.HOUSE_RECT = (x0, x1, y0+18, y1+18)
    ridge.HOUSE_WINDOWS = [(x, y+18) for x, y in ridge.HOUSE_WINDOWS]
    x, y, w, h = ridge.DOOR_TRIGGER
    ridge.DOOR_TRIGGER = (x, y+18, w, h)
    ridge.PORCH_ROW += 18
    links = []
    for link in scene_links.REDESIGN[2]:
        if link.source == ridge.RIDGE:
            link = replace(link, rect=(62, 12, 1, 3), entry=(2, 26))
        else:
            x, y, w, h = link.rect
            link = replace(link, rect=(x, y+18, w, h))
            if link.target == ridge.RIDGE:
                link = replace(link, entry=(56, 14))
        links.append(link)
    scene_links.REDESIGN = {**scene_links.REDESIGN, 2: tuple(links)}

    layout = copy.deepcopy(ridge.RIDGE_LAYOUT)
    layout.MAP_H, layout.GROUND_ROW = 36, 33
    layout.NAME = 'Wind Ridge - Route Pilot 3'
    layout.SOLID_BLOCKS = [(0, 0, 2, 32), (63, 63, 2, 32), (5, 7, 30, 32), *TERRACES, WIND_ROOF]
    layout.BLOCKS = [(5, 7, 30, 32), *TERRACES, WIND_ROOF]
    layout.LEDGES, layout.BOARDS = [(27, 9, 14)], [(27, 9, 11)]
    layout.GUST_LANES, layout.GUST_START_DELAYS = [(19, 31, 33)], [30]
    layout.WHIP_LANES, layout.WHIP_START_DELAYS = [(13, 45, 46)], [50]
    layout.HIDDEN_CABLES, layout.CABLE_START_DELAYS = [(13, 58, 59)], [0]
    layout.FALLEN_SPANS = []
    layout.START, layout.ENTRIES = START, [START, (56, 14)]
    layout.WIRE_ROUTES = [
        (1, [(0, 22), (6, 22), (6, 26)]),
        (1, [(6, 22), (16, 22), (16, 23)]),
        (1, [(16, 22), (20, 22), (20, 23)]),
        (2, [(20, 23), (21, 23), (21, 17), (34, 17), (34, 13), (36, 13), (36, 14)]),
        (2, [(36, 13), (40, 13), (40, 14)]),
        (3, [(40, 14), (41, 14), (41, 3), (63, 3)]),
    ]
    # Final-pole pickup is at floor level. The overhead route no longer connects
    # to the porch, and the visible rock arch prevents vaulting the whole field.
    saddle.MAP_H, saddle.GROUND_ROW = 36, 33
    saddle.NAME = 'Ridge Saddle - Route Pilot 3'
    relative_blocks = [(1, 4, 12, 14), (13, 18, 12, 14),
                       (32, 36, 12, 14), (54, 62, 12, 14)]
    saddle.BLOCKS = [(a,b,c+18,d+18) for a,b,c,d in relative_blocks] + [SADDLE_ROOF]
    saddle.SOLID_BLOCKS = [(0,0,2,32),(63,63,2,32),*saddle.BLOCKS]
    saddle.LEDGES = [(27,1,4),(27,20,31)]
    saddle.BOARDS = [(27,21,23)]
    saddle.GUST_LANES = [(25,26,28), (31,49,51)]
    saddle.WHIP_LANES, saddle.WHIP_START_DELAYS = [], []
    saddle.HIDDEN_CABLES, saddle.CABLE_START_DELAYS = [(31,9,10)], [40]
    saddle.FALLEN_SPANS = [{'columns': (40,46), 'live_after': 4, 'arcs': [(31,41,42)], 'delays': [40]}]
    saddle.first_hazard = {'gust': 3, 'whip': 3, 'span': 2, 'cable': 3, 'board': 3}
    saddle.START, saddle.ENTRIES = (2,26), [(2,26)]
    saddle.HOUSE_WINDOWS = ridge.HOUSE_WINDOWS
    routes = [
        (3,[(0,3),(14,3),(14,8)]),
        (3,[(14,3),(18,3),(18,8)]),
        (4,[(18,8),(19,8),(19,4),(33,4),(33,8)]),
        (4,[(33,4),(37,4),(37,11)]),
        (5,[(37,11),(38,11),(50,11),(50,7),(54,7),(54,8)]),
    ]
    saddle.WIRE_ROUTES = [(stage,[(x,y+18) for x,y in route]) for stage,route in routes]
    # Incoming stage3 stays at its existing Wind edge height; descend beside the
    # wall before joining the copied Saddle wire run.
    saddle.WIRE_ROUTES[0] = (3,[(0,3),(1,3),(1,21),(14,21),(14,26)])
    for current in (layout, saddle):
        current.LAKESIDE = False
        current.LINES = grid_chain.scene_lines(ridge.LINES, current.folder)
        current.links = scene_links.from_scene(current.folder, scene_links.table('redesign'))
        current.arrivals = scene_links.into_scene(current.folder, scene_links.table('redesign'))
        current.EXITS = [link.rect for link in current.links]
        current.EXIT = next(link.rect for link in current.links if link.target != ridge.RIDGE)
    ridge.LAYOUTS = {ridge.RIDGE: layout, ridge.SADDLE: saddle}
    ridge.RIDGE_LAYOUT, ridge.SADDLE_LAYOUT = layout, saddle
    return layout


def validate_contract(layout):
    grid = layout.collision_grid()
    assert len(grid) == 36 and all(len(row) == 64 for row in grid)
    props = list(layout.ENTRIES)
    for line in layout.LINES:
        props += [line[k] for k in ('pole','box','checkpoint') if k in line]
    if layout.HOUSE:
        props += [ridge.TOMAS, ridge.CONCENTRATOR]
    grid_chain.check_props(grid, props, layout.hazard_cells(), ridge.HUD_ROWS)
    for row,x0,x1 in layout.all_hazard_lanes():
        assert all(grid[row][x] == ridge.COL_EMPTY and grid[row+2][x] in
                   (ridge.COL_TOP,ridge.COL_SOLID) for x in range(x0,x1+1))
    assert layout.actor_count() <= ridge.MAX_SCENE_ACTORS
    return grid


def case_settings(case):
    cases = {
        None: (ridge.RIDGE, START, {'16':2}),
        'gust': (ridge.RIDGE, (27,23), {'16':0,'17':1,'18':1,'20':1,'6':2}),
        'summit': (ridge.RIDGE, (54,14), {'16':0,'17':1,'28':1,'18':2,'20':2,'6':3}),
        'saddle': (ridge.SADDLE, (37,32), {'16':0,'17':1,'28':1,'19':1,'29':1,'18':4,'20':4,'6':5}),
    }
    folder, start, values = cases[case]
    return folder, start, {**values, '55':1}


def generate(case=None):
    folder, start, values = case_settings(case)
    name = 'ridge-route-pilot' + (f'-{case}' if case else '')
    destination = diagnostics.fixture(name, folder, *start, {})
    configure_contract()
    import make_ridge_art as art
    import make_ridge_scene as scene
    import make_climb_scene as shared
    art.ROOT, scene.PROJECT_DIR = destination, destination
    scene.SCENES_DIR = destination / 'project/scenes'
    # Draw the original Saddle trees in the translated local framing.
    art.PINES[ridge.SADDLE] = [(x, top+144) for x,top in art.PINES[ridge.SADDLE]]
    variables_path = destination / 'project/variables.gbsres'
    variables = json.loads(variables_path.read_text())
    assert not any(v['id']=='55' for v in variables['variables']), 'fixture flag occupied'
    variables['variables'].append({'id':'55','name':'Route Pilot Started','symbol':'var_route_pilot_started'})
    shared.write_json(variables_path,variables)
    music,audio,sprites = scene.audio_and_sprite_ids()
    for current in ridge.LAYOUTS.values():
        validate_contract(current)
        renderer = art.SceneArt(current.folder)
        renderer.MAX_UNIQUE_TILES = 256
        renderer.write()
        authored,_ = renderer.make_background()
        image_name = 'route-pilot-author.png' if current.folder == ridge.RIDGE else 'saddle-pilot-author.png'
        authored.save(destination / image_name)
        builder = scene.SceneBuilder(current.folder)
        native_scene = builder.build_scene(music,audio)
        if current.folder == folder:
            native_scene['script'] = [builder.if_value('55',0,'pilot-first-visit',diagnostics.seed(values))] + native_scene['script']
        shared.write_json(builder.scene_dir / 'scene.gbsres',native_scene)
        for kind,items in [('actors',builder.build_actors(sprites)),('triggers',builder.build_triggers(audio))]:
            directory = builder.scene_dir / kind
            keep = {f"{item['symbol']}.gbsres" for item in items}
            for stale in directory.glob('*.gbsres'):
                if stale.name not in keep:
                    stale.unlink()
            for item in items:
                shared.write_json(directory / f"{item['symbol']}.gbsres",item)
        for relative,resource in builder.box_script_resources(audio):
            shared.write_json(destination / relative,resource)
    manifest = {'revision':3,'scene':folder,'size':[64,36],'start':start,
                'case':case or 'normal-route','seed':values,'terraces':TERRACES,
                'roofs':{'wind_ridge':WIND_ROOF,'ridge_saddle':SADDLE_ROOF},
                'lines':ridge.LINES,'layouts':{f:{'hazards':c.lanes(),'boards':c.BOARDS,
                 'entries':c.ENTRIES,'exits':c.EXITS} for f,c in ridge.LAYOUTS.items()},
                'source_scope':'isolated fixture; production unchanged','runtime_validation':'pending'}
    (destination/'route-pilot.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(destination/'mr-cfe.gbsproj')
    return destination


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',choices=('gust','summit','saddle'))
    generate(parser.parse_args().case)
