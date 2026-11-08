"""Isolated walkable WO-0413 hub; production and original map stay unchanged.

Managed Python: tools/make_dispatch_hub.py [--unlit]
Outputs only build/diagnostics/dispatch-hub[-unlit]. Seeded diagnostic, not campaign.
"""
from copy import deepcopy
from pathlib import Path
import argparse
import json
import shutil
from PIL import Image, ImageDraw
import dispatch_map as contract
import make_dispatch_map as map_art
import make_campaign_diagnostics as diagnostics
import make_intro_sprites as sprite_art
import make_ticket_scene as ticket
import make_climb_scene as shared
import neighborhood_hero

W = H = 32
START = (15, 13)
FIXTURE_INIT_VAR = '56'
# House names, real completion variables, dedicated light slots, pixel origins.
HOMES = tuple((*home[:3], x, y) for home, (x, y) in zip(contract.HOMES,
              ((32, 56), (192, 56), (32, 168), (192, 168))))
NEAR_VAR = '27'  # Existing scene-local interaction scratch, reset on scene entry.
BACKGROUND_ID = contract.tickets.resource_id('background:dispatch-walkable')
HERO_ID = contract.tickets.resource_id('sprite:dispatch-walkable-hero')

def rid(key):
    return contract.tickets.resource_id('dispatch-hub:' + key)

def ev(command, args, key, children=None):
    return ticket.ev(command, args, 'hub:' + key, children)

def set_near(n, key):
    return ev('EVENT_SET_VALUE', {'variable': NEAR_VAR, 'value': shared.number(n)}, key)

def build_art():
    """Reuse exact house/label pixels; expand lawn/path space for a 32px hero."""
    source, source_slots = map_art.build_art()
    idx = Image.new('L', (W*8, H*8), 1)
    slots = [[1]*W for _ in range(H)]
    d = ImageDraw.Draw(idx)
    d.rectangle((0, 0, 255, 15), fill=0)
    for row in (0, 1): slots[row] = [0]*W
    # Generic original home names remain valid for every actual dispatch value.
    # The once-only welcome and A guidance identify the current assignment.
    for home, old in zip(HOMES, contract.HOMES):
        name, variable, slot, x, y = home
        ox, oy = old[3:]
        idx.paste(source.crop((ox, oy-8, ox+32, oy+32)), (x, y-8))
        for ty in range(-1, 4):
            for tx in range(4):
                slots[y//8+ty][x//8+tx] = source_slots[oy//8+ty][ox//8+tx]
        # Path widens immediately below the doorway. All are safe walking lanes.
        d.rectangle((x, y+32, x+31, y+47), fill=2)
        d.line((x+16, y+40, 128, y+40), fill=2, width=12)
        # Small repeated approach marks clarify the interactive doorstep.
        d.line((x+6, y+34, x+10, y+34), fill=3)
    d.line((128, 96, 128, 216), fill=2, width=16)
    for x, y in ((80,56),(160,48),(88,168),(160,184),(72,232),(176,232)):
        d.line((x,y,x+3,y),fill=2)
    return idx, slots

def collision_grid():
    grid = [[0]*W for _ in range(H)]
    # Foot collision only: house footprints and perimeter, no invisible path rails.
    for y in range(H):
        for x in range(W):
            if x in (0,W-1) or y < 3 or y == H-1: grid[y][x] = 15
    for _,_,_,px,py in HOMES:
        for y in range(py//8, py//8+4):
            for x in range(px//8, px//8+4): grid[y][x] = 15
    return grid

def assignment_hint():
    body=[ticket.dialogue(['No active order.'], 'hub:no-order')]
    for n, (name,_,_,_,_) in reversed(list(enumerate(HOMES,1))):
        body=[ticket.if_value('16',n,'hub:hint-ticket-'+str(n),
              [ticket.dialogue(['Next: '+name+'\nWalk to the door.\nPress A there.'],
                               'hub:hint-'+str(n))],body)]
    return body

def interaction_script():
    body = assignment_hint()
    for n, home in reversed(list(enumerate(HOMES, 1))):
        name, variable = home[:2]
        target = contract.tickets.TICKETS[n]
        # Real dispatch chooses the available job; completion still owns its light.
        accept = [ticket.dialogue([name+'\nA: take the job'], 'hub:accept-'+str(n)),
                  set_near(0, 'leave-zone-'+str(n)), ticket.fade_out('hub:fade-'+str(n)),
                  ticket.switch_scene(target['scene_id'], *target['start'], 'right', 'hub:job-'+str(n))]
        unavailable=[ticket.dialogue([name+'\nStill waiting.'], 'hub:waiting-'+str(n)),*assignment_hint()]
        events = [ticket.if_value(variable,1,'hub:home-'+str(n),
            [ticket.dialogue([name+'\nPower restored.'], 'hub:restored-'+str(n))],
            [ticket.if_value('16',n,'hub:ticket-'+str(n),accept,unavailable)])]
        body = [ticket.if_value(NEAR_VAR, n, 'hub:near-'+str(n), events, body)]
    return ev('EVENT_SET_INPUT_SCRIPT', {'input':['a'], 'override':True}, 'interact', {'true':body})

def build_scene():
    scene = ticket.build_scenes()['work_order']
    scene.update(name='Neighborhood Hub Prototype', width=W, height=H,
                 backgroundId=BACKGROUND_ID, paletteIds=contract.PALETTE_IDS,
                 playerSpriteSheetId=HERO_ID,
                 collisions=shared.collision_rle(collision_grid(),W,H))
    # Take only the flag-driven lighting from the fixed map; no modal dispatch.
    light_script = [deepcopy(e) for e in map_art.prototype_scene()['script'] if e['command']=='EVENT_IF']
    scene['script'] = [ticket.overlay_hide('hub:overlay'),
        ev('EVENT_OVERLAY_SET_SCANLINE_CUTOFF', {'units':'pixels','y':shared.number(150)}, 'cutoff'),
        ev('EVENT_ACTOR_SHOW', {'actorId':'player'}, 'show'),
        ev('EVENT_ACTOR_SET_MOVEMENT_SPEED', {'actorId':'player','speed':1}, 'speed'),
        set_near(0,'clear-zone'), *light_script, interaction_script()]
    return scene

def build_triggers():
    triggers=[]
    for n, (name,_,_,x,y) in enumerate(HOMES,1):
        triggers.append({'_resourceType':'trigger','id':rid('door:'+name),'_index':n-1,
            'name':name+' doorstep','symbol':'trigger_hub_'+name.lower(),
            'x':x//8,'y':y//8+4,'width':4,'height':2,
            'script':[set_near(n,'enter-'+name)], 'leaveScript':[set_near(0,'exit-'+name)]})
    return triggers

def hero_frames():
    """Keep right-facing source exact; author front/back faces and mirror left.

    The hard hat, jacket and walk timing remain the accepted Neighborhood Hero.
    Separate asset avoids modifying any intro frames or platformer bounds.
    """
    right = [neighborhood_hero.NEIGHBORHOOD_FRAMES[i] for i in (0,2,4)]
    left = [tuple(row[::-1] for row in frame) for frame in right]
    front, back = [], []
    for frame in right:
        f=list(frame); b=list(frame)
        f[10:17]=('...332222233....','...322222223....','...323223223....',
                  '...322222223....','....3222223.....','....3322233.....','...33223333.....')
        b[10:17]=('...333333333....','...333333333....','...333333333....',
                  '...333333333....','....3333333.....','....3322233.....','...33223333.....')
        # Back has a reflective jacket band, no front pockets or belt buckle.
        b[18]='.3222222222223..'; b[20]='.3311111111133..'
        b[24]='.3113333333313..'
        front.append(tuple(f));back.append(tuple(b))
    return right+left+back+front

def build_hero():
    frames=hero_frames()
    sheet=Image.new('RGBA',(16*len(frames),32),(0,0,0,0))
    for i,frame in enumerate(frames): sheet.paste(sprite_art._render(frame,32),(i*16,0))
    animations=[]; signatures=set()
    indices=[[0],[3],[6],[9],[1,0,2,0],[4,3,5,3],[7,6,8,6],[10,9,11,9]]
    for ai, seq in enumerate(indices):
        output=[]
        for fi,frame_index in enumerate(seq):
            tiles=[]
            for x in (0,8):
                for y in (0,16):
                    signatures.add(sheet.crop((frame_index*16+x,y,frame_index*16+x+8,y+16)).tobytes())
                    tiles.append({'id':rid(f'tile:{ai}:{fi}:{x}:{y}'),'x':x,'y':16-y,
                        'sliceX':frame_index*16+x,'sliceY':y,'flipX':False,'flipY':False,
                        'palette':0,'paletteIndex':0,'objPalette':'OBP0','priority':False})
            output.append({'id':rid(f'frame:{ai}:{fi}'),'tiles':tiles})
        animations.append({'id':rid('anim:'+str(ai)),'frames':output})
    meta={'_resourceType':'sprite','id':HERO_ID,'name':'dispatch_hub_hero',
        'symbol':'sprite_dispatch_hub_hero','filename':'dispatch_hub_hero.png',
        'width':sheet.width,'height':32,'checksum':'','numTiles':len(signatures),
        'canvasOriginX':0,'canvasOriginY':0,'canvasWidth':16,'canvasHeight':32,
        'boundsX':3,'boundsY':0,'boundsWidth':10,'boundsHeight':8,
        'animSpeed':10,'spriteMode':'8x16','states':[{'id':rid('state'), 'name':'',
        'animationType':'multi_movement','flipLeft':False,'animations':animations}]}
    return sheet,meta

def fixture_scene(values):
    scene=build_scene()
    # A diagnostic boot seed runs once only, so returning from a job preserves
    # its earned home flags and the next actual dispatch ticket.
    init=diagnostics.seed(values)+[ev('EVENT_SET_VALUE',
         {'variable':FIXTURE_INIT_VAR,'value':shared.number(1)},'fixture-initialized')]
    scene['script']=[ticket.if_value(FIXTURE_INIT_VAR,0,'hub:first-entry',init,[])]+scene['script']
    scene['script'].append(ticket.if_value(FIXTURE_INIT_VAR,1,'hub:first-help',
        [*assignment_hint(),ev('EVENT_SET_VALUE',{'variable':FIXTURE_INIT_VAR,
          'value':shared.number(2)},'help-shown')],[]))
    return scene

def write_prototype(unlit=False):
    values={'0':0 if unlit else 1,'9':0,'11':0,'13':0,'16':2}
    destination=diagnostics.fixture('dispatch-hub-unlit' if unlit else 'dispatch-hub',
                                    'work_order',*START,values)
    folder=destination/'project/scenes/work_order'
    # Only diagnostic subfolders are replaced; original static-map actor cannot leak in.
    for name in ('actors','triggers'):
        path=folder/name
        if path.exists(): shutil.rmtree(path)
        path.mkdir()
    scene=fixture_scene(values)
    variables_path=destination/'project/variables.gbsres'
    variables=json.loads(variables_path.read_text())
    existing=[v for v in variables['variables'] if v['id']==FIXTURE_INIT_VAR]
    if existing and existing[0].get('symbol')!='var_dispatch_hub_initialized':
        raise ValueError('Fixture initialization variable is already owned')
    if not existing:
        variables['variables'].append({'id':FIXTURE_INIT_VAR,'name':'Hub fixture initialized',
                                      'symbol':'var_dispatch_hub_initialized'})
    shared.write_json(variables_path,variables)
    shared.write_json(folder/'scene.gbsres',scene)
    for i,trigger in enumerate(build_triggers()):
        shared.write_json(folder/'triggers'/f'door_{i}.gbsres',trigger)
    idx,slots=build_art(); bg=destination/'assets/backgrounds/dispatch_hub.png'
    idx.point([255,170,85,0]+[0]*252).convert('RGB').save(bg,optimize=False)
    shared.write_json(Path(str(bg)+'.gbsres'),{'_resourceType':'background',
        'id':BACKGROUND_ID,'name':'dispatch_hub','symbol':'bg_dispatch_hub',
        'filename':bg.name,'width':W,'height':H,'imageWidth':256,'imageHeight':256,
        'autoColor':False,'tileColors':shared.collision_rle(slots,W,H)})
    for name,colors in contract.PALETTES.items():
        shared.write_json(destination/'project/palettes'/f'dispatch_{name}.gbsres',{
            '_resourceType':'palette','id':contract.palette_id(name),'name':'Dispatch '+name,'colors':colors})
    sheet,meta=build_hero(); sp=destination/'assets/sprites/dispatch_hub_hero.png'
    sheet.save(sp);shared.write_json(Path(str(sp)+'.gbsres'),meta)
    print('Isolated walkable hub:',destination/'mr-cfe.gbsproj')
    return destination

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unlit',action='store_true')
    write_prototype(parser.parse_args().unlit)
