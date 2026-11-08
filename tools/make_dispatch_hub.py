"""Walkable production lakeside hub plus an isolated diagnostic fixture.

Managed Python: tools/make_dispatch_hub.py [--unlit]
``write_production`` writes the campaign hub; CLI still writes only an isolated,
seeded diagnostic fixture.
"""
from pathlib import Path
import argparse
import json
import shutil
from PIL import Image, ImageDraw
import dispatch_map as contract
import make_campaign_diagnostics as diagnostics
import make_intro_sprites as sprite_art
import make_ticket_scene as ticket
import make_climb_scene as shared
import neighborhood_hero

W = H = 32
START = (15, 13)
FIXTURE_INIT_VAR = '56'
# District names, real completion variables, dedicated light slots, pixel origins.
DISTRICTS = tuple((*home[:3], x, y) for home, (x, y) in zip(contract.HOMES,
                  ((32, 144), (192, 144), (32, 184), (192, 184))))
NEAR_VAR = '27'  # Existing scene-local interaction scratch, reset on scene entry.
BACKGROUND_ID = contract.tickets.resource_id('background:dispatch-walkable')
HERO_ID = contract.tickets.resource_id('sprite:dispatch-walkable-hero')
WATER_PALETTE_ID = contract.tickets.resource_id('dispatch-hub:palette:lakeside-water')
PALETTE_IDS = [contract.PALETTE_IDS[0], contract.PALETTE_IDS[1], WATER_PALETTE_ID,
               *[contract.palette_id('off')]*4, 'default-ui']
WATER_COLORS = ['0B101E', '173B50', '39728A', '9BC6C2']

def rid(key):
    return contract.tickets.resource_id('dispatch-hub:' + key)

def ev(command, args, key, children=None):
    return ticket.ev(command, args, 'hub:' + key, children)

def set_near(n, key):
    return ev('EVENT_SET_VALUE', {'variable': NEAR_VAR, 'value': shared.number(n)}, key)

def build_art():
    """Make a compact lakeside commons with four signed, non-residential trails."""
    idx = Image.new('L', (W*8, H*8), 1)
    slots = [[1]*W for _ in range(H)]
    d = ImageDraw.Draw(idx)
    # Distant ridges above open water. Repeating ripple tiles keep the
    # lake legible even when the camera shows only a portion of the shore.
    d.rectangle((0, 0, 255, 15), fill=0)
    for row in (0, 1):
        slots[row] = [0]*W
    d.rectangle((0, 16, 255, 63), fill=2)
    for row in range(2, 8):
        slots[row] = [2]*W
    d.polygon([(0,21),(26,16),(47,23),(74,17),(109,27),(133,19),
               (160,26),(193,16),(218,22),(240,17),(255,21),
               (255,31),(0,31)], fill=1)
    for y in (32, 40, 48, 56):
        for x in range(0, 256, 8):
            # The square and row offset break the appearance of a tiled grid.
            pattern = ((x//8 + y//4)**2 + y//8) % 7
            if pattern == 1:
                d.line((x+1,y+2,x+6,y+2), fill=3)
            elif pattern in (2, 4):
                d.line((x+2,y+5,x+5,y+5), fill=1)
    # One uneven run of bright shallows borders the dark near shore.
    for x in range(0, 256, 8):
        y = 58 + (0, 1, 2, 1)[(x//8) % 4]
        d.line((x,y,x+7,y), fill=1)
        if (x//8) % 3 != 1:
            d.line((x+1,y,x+7,y), fill=3)
        d.rectangle((x,y+1,x+7,63), fill=1)
    d.rectangle((0, 64, 255, 71), fill=2)
    for x in range(0, 256, 8):
        if (x//8) % 3 == 2:
            d.line((x+1,65,x+4,65), fill=3)
        elif (x//8) % 3 == 0:
            d.line((x+5,68,x+7,68), fill=1)

    # Promenade and its plaza share stonework; thinner paths lead to signs.
    d.line((128,72,128,239), fill=2, width=16)
    d.rectangle((112,128,143,183), fill=2)
    d.line((48,156,208,156), fill=2, width=16)
    d.line((48,176,208,176), fill=2, width=16)
    d.line((48,156,48,231), fill=2, width=16)
    d.line((208,156,208,231), fill=2, width=16)
    for y in range(72, 248, 8):
        for x in range(8, 248, 8):
            pattern = ((x//8 + y//8)**2 + y//8) % 9
            if idx.getpixel((x,y)) == idx.getpixel((x+7,y+7)) == 2:
                if pattern in (0, 2, 5):
                    d.line((x+2,y+3,x+4,y+3), fill=3)
                    d.point((x+4,y+4), fill=1)
            elif idx.getpixel((x+3,y+3)) == 1:
                if pattern == 1:
                    d.point((x+3,y+5), fill=2)
                    d.line((x+4,y+4,x+5,y+4), fill=2)
                elif pattern == 3:
                    d.point((x+1,y+3), fill=2)
                    d.line((x+2,y+5,x+4,y+5), fill=2)

    # Shore pines and rocks are set into the impassable bank, with the
    # silhouettes repeated at tile-aligned offsets.
    for x in (8, 32, 64, 216, 240):
        d.rectangle((x+6,65,x+8,71), fill=0)
        for y, half_width in ((45,4), (51,6), (57,7)):
            d.polygon([(x+7,y),(x+7-half_width,y+9),(x+7+half_width,y+9)], fill=0)
            d.line((x+7,y+1,x+4,y+6), fill=3)
    for x in (16, 48, 80, 200, 224):
        d.polygon([(x+1,70),(x+2,66),(x+5,65),(x+7,68),(x+7,70)], fill=0)
        d.line((x+2,67,x+5,66), fill=3)

    # Power shed. A lightning sign and roll-up work bay distinguish it
    # from the households. Its footprint stays north of the district paths.
    d.rectangle((152,104,199,111), fill=2)
    d.rectangle((154,88,197,108), fill=0)
    d.rectangle((156,91,195,104), fill=3)
    d.polygon([(152,88),(158,80),(193,80),(199,88),(199,90),(152,90)], fill=0)
    d.polygon([(155,87),(160,81),(191,81),(196,87)], fill=2)
    d.line((160,82,191,82), fill=3)
    d.rectangle((163,93,179,104), fill=0)
    for y in (95, 98, 101):
        d.line((165,y,177,y), fill=2)
    d.rectangle((183,93,192,102), fill=2)
    d.polygon([(189,94),(185,98),(188,98),(187,101),(191,97),(188,97)], fill=3)
    # Trailheads are signs and route lamps, never copies of the residents' homes.
    for name, variable, slot, x, y in DISTRICTS:
        cx=x+16
        d.rectangle((cx-1,y+13,cx+1,y+31),fill=0)
        d.rectangle((x,y,x+31,y+14),fill=0)
        d.rectangle((x+1,y+1,x+30,y+13),fill=2)
        text(idx, name, cx, y+3)
        # Lamp is a flag-driven palette tile; restored routes glow warm yellow.
        d.rectangle((cx-4,y+31,cx+4,y+39),fill=0)
        d.rectangle((cx-2,y+33,cx+2,y+37),fill=3)
        slots[(y+32)//8][cx//8] = slot
    # A quiet lake-facing bench gives the arrival a natural pause/view.
    d.rectangle((91,119,115,124),fill=0)
    d.rectangle((94,120,112,122),fill=3)
    d.rectangle((94,123,96,128),fill=0); d.rectangle((110,123,112,128),fill=0)
    return idx, slots

def text(image,word,cx,y):
    """Render small district labels into the background, without runtime fonts."""
    font={
        'A':['010','101','111','101','101'],'E':['111','100','110','100','111'],
        'H':['101','101','111','101','101'],'I':['111','010','010','010','111'],
        'M':['101','111','111','101','101'],'N':['101','111','111','111','101'],
        'O':['010','101','101','101','010'],'P':['110','101','110','100','100'],
        'R':['110','101','110','101','101'],'S':['011','100','010','001','110'],
        'Y':['101','101','010','010','010'],'L':['100','100','100','100','111'],
        ' ':['000']*5,
    }
    width=len(word)*4-1; x=cx-width//2
    draw=ImageDraw.Draw(image)
    for char in word:
        for yy,row in enumerate(font[char]):
            for xx,pixel in enumerate(row):
                if pixel=='1': draw.point((x+xx,y+yy),fill=3)
        x+=4

def collision_grid():
    grid = [[0]*W for _ in range(H)]
    # Foot collision only: shoreline, depot, signboards, and perimeter.
    for y in range(H):
        for x in range(W):
            if x in (0,W-1) or y < 3 or y == H-1: grid[y][x] = 15
            if 2 <= y <= 8: grid[y][x] = 15
    for y in range(10, 14):
        for x in range(19, 25):
            grid[y][x] = 15
    for _,_,_,px,py in DISTRICTS:
        # Signboards and lamps are solid visual landmarks, but leave the approach
        # tile open so the player can stand directly in front of each sign.
        for y in range(py//8, py//8+2):
            for x in range(px//8, px//8+4): grid[y][x] = 15
    return grid

def assignment_hint(prefix='hub:hint'):
    body=[ticket.dialogue(['No active order.'], prefix+':no-order')]
    for n, (name,_,_,_,_) in reversed(list(enumerate(DISTRICTS,1))):
        body=[ticket.if_value('16',n,prefix+':ticket-'+str(n),
              [ticket.dialogue(['Next: '+name+'\nGo to trail sign.\nPress A there.'],
                               prefix+':text-'+str(n))],body)]
    return body

def interaction_script():
    return interactions()

def build_scene():
    scene_index = next(i for i, row in enumerate(contract.tickets.SCENES)
                       if row[0] == contract.tickets.WORK_ORDER_SCENE_ID)
    scene_meta = contract.tickets.SCENES[scene_index]
    scene = ticket.scene_resource(scene_meta[0], scene_meta[1],
        'Lakeside Town', scene_index, scene_meta[-2], scene_meta[-1], [])
    scene.update(name='Lakeside Town', width=W, height=H,
                 backgroundId=BACKGROUND_ID, paletteIds=PALETTE_IDS,
                 playerSpriteSheetId=HERO_ID,
                 collisions=shared.collision_rle(collision_grid(),W,H))
    # Each trailhead lamp reflects only its real, persistent home completion flag.
    light_script=[]
    for name, variable, slot, _, _ in DISTRICTS:
        on_args={f'palette{i}':'keep' for i in range(8)}
        on_args[f'palette{slot}']=contract.palette_id('on')
        off_args={f'palette{i}':'keep' for i in range(8)}
        off_args[f'palette{slot}']=contract.palette_id('off')
        on=ev('EVENT_PALETTE_SET_BACKGROUND',on_args,'lamp-on:'+name.lower())
        off=ev('EVENT_PALETTE_SET_BACKGROUND',off_args,'lamp-off:'+name.lower())
        light_script.append(ticket.if_value(variable,1,'lamp:'+name.lower(),[on],[off]))
    scene['script'] = [ticket.overlay_hide('hub:overlay'),
        ev('EVENT_OVERLAY_SET_SCANLINE_CUTOFF', {'units':'pixels','y':shared.number(150)}, 'cutoff'),
        ev('EVENT_ACTOR_SHOW', {'actorId':'player'}, 'show'),
        ev('EVENT_ACTOR_SET_MOVEMENT_SPEED', {'actorId':'player','speed':1}, 'speed'),
        set_near(0,'clear-zone'), *light_script, interaction_script()]
    return scene

def interactions():
    """Build interactions and remove the A override before leaving town."""
    body=assignment_hint('hub:default-hint')
    for n, home in reversed(list(enumerate(DISTRICTS,1))):
        name, variable=home[:2]
        target=contract.tickets.TICKETS[n]
        remove_a=ev('EVENT_REMOVE_INPUT_SCRIPT',{'input':['a']},'restore-a-default-'+str(n))
        accept=[ticket.dialogue(target['pages'],'hub:accept-'+str(n)),
                set_near(0,'leave-zone-'+str(n)),remove_a,
                ticket.fade_out('hub:fade-'+str(n)),
                ticket.switch_scene(target['scene_id'],*target['start'],'right','hub:job-'+str(n))]
        unavailable=[ticket.dialogue([name+'\nStill waiting.'],'hub:waiting-'+str(n)),
                     *assignment_hint('hub:unavailable-'+str(n))]
        events=[ticket.if_value(variable,1,'hub:home-'+str(n),
                [ticket.dialogue([name+'\nPower restored.'],'hub:restored-'+str(n))],
                [ticket.if_value('16',n,'hub:ticket-'+str(n),accept,unavailable)])]
        body=[ticket.if_value(NEAR_VAR,n,'hub:near-'+str(n),events,body)]
    return ev('EVENT_SET_INPUT_SCRIPT',{'input':['a'],'override':True},'interact',{'true':body})

def build_triggers():
    triggers=[]
    for n, (name,_,_,x,y) in enumerate(DISTRICTS,1):
        triggers.append({'_resourceType':'trigger','id':rid('trail:'+name),'_index':n-1,
            'name':name+' district trail','symbol':'trigger_hub_'+name.lower(),
            'x':x//8,'y':y//8+2,'width':4,'height':2,
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
        # Preserve the accepted side frames; give vertical views a centered
        # helmet and face instead of painting a face across the side brim.
        helmet=('.....333333.....','....33111133....','...3311111133...',
                '...3111111113...','..333333333333..')
        f[8:17]=helmet+('....31111113....','....31311313....',
                       '.....311113.....','.....333333.....')
        b[8:17]=helmet+('....33333333....','....33333333....',
                       '.....333333.....','.....333333.....')
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
    # Authored slots: right, left, up, down. The official compiler's
    # toEngineOrder maps these to down/right/up/left at runtime.
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

def write_production():
    """Write the unseeded production scene, trail triggers, and native assets."""
    root=Path(__file__).resolve().parent.parent
    scene_folder=root/'project/scenes/work_order'
    (scene_folder/'triggers').mkdir(parents=True,exist_ok=True)
    shared.write_json(scene_folder/'scene.gbsres',build_scene())
    for i,trigger in enumerate(build_triggers()):
        shared.write_json(scene_folder/'triggers'/f'dispatch_trail_{i}.gbsres',trigger)
    idx,slots=build_art()
    bg=root/'assets/backgrounds/dispatch_hub.png'
    idx.point([255,170,85,0]+[0]*252).convert('RGB').save(bg,optimize=False)
    shared.write_json(Path(str(bg)+'.gbsres'),{
        '_resourceType':'background','id':BACKGROUND_ID,'name':'dispatch_hub',
        'symbol':'bg_dispatch_hub','filename':bg.name,'width':W,'height':H,
        'imageWidth':W*8,'imageHeight':H*8,'autoColor':False,
        'tileColors':shared.collision_rle(slots,W,H)})
    for name,colors in contract.PALETTES.items():
        shared.write_json(root/'project/palettes'/f'dispatch_{name}.gbsres',{
            '_resourceType':'palette','id':contract.palette_id(name),
            'name':'Dispatch '+name,'colors':colors})
    shared.write_json(root/'project/palettes/dispatch_lakeside_water.gbsres',{
        '_resourceType':'palette','id':WATER_PALETTE_ID,
        'name':'Lakeside Water','colors':WATER_COLORS})
    sheet,meta=build_hero(); sp=root/'assets/sprites/dispatch_hub_hero.png'
    sheet.save(sp); shared.write_json(Path(str(sp)+'.gbsres'),meta)
    return scene_folder

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unlit',action='store_true')
    write_prototype(parser.parse_args().unlit)
