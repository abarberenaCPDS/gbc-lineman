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
import storm_worker_topdown

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
# Solid footprints are declared once for the renderer and collision map.
BUILDINGS = ((4, 10, 7, 'DEPOT'), (20, 10, 6, 'WORKS'))
PLANTERS = ((2, 11, 2), (27, 11, 2), (8, 18, 4), (20, 18, 4),
            (8, 23, 4), (20, 23, 4), (5, 29, 6), (21, 29, 6))
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

    # Repeat a few native stone, timber and turf motifs. Tile-aligned streets
    # connect the waterfront, both rows of kiosks, and the southern green.
    paving = {(x, 9) for x in range(1, 31)}
    paving |= {(x, y) for x in range(13, 19) for y in range(9, 29)}
    paving |= {(x, y) for x in range(2, 30) for y in (15, 16, 17, 20, 21, 22, 25, 26, 27)}
    for ty in range(9, 32):
        for tx in range(32):
            x, y = tx*8, ty*8
            pattern = (tx*3+ty*5) % 7
            if (tx, ty) in paving:
                slots[ty][tx] = 0
                d.rectangle((x,y,x+7,y+7), fill=1)
                d.line((x,y+1,x+7,y+1), fill=2)
                d.point((x+3+(ty%2)*3,y+2), fill=2)
                if pattern < 2:
                    d.line((x+2,y+5,x+5,y+5), fill=2)
            elif pattern in (1, 3, 5):
                d.line((x+2,y+5,x+4,y+5), fill=2)
                d.point((x+4,y+4), fill=2)

    # Boardwalk on the north edge of the street; only the center dock crosses
    # the shoreline. Rail posts occupy solid tiles on either side.
    for tx in range(1,31):
        x = tx*8
        slots[8][tx] = 0
        d.rectangle((x,64,x+7,71), fill=1)
        d.line((x,66,x+7,66), fill=3)
        d.line((x,69,x+7,69), fill=2)
        if tx % 2:
            d.rectangle((x+1,64,x+2,71), fill=0)
    for ty in range(5,9):
        for tx in range(14,18):
            x,y = tx*8,ty*8
            slots[ty][tx] = 0
            d.rectangle((x,y,x+7,y+7),fill=2)
            d.line((x,y+3,x+7,y+3),fill=1)
            d.line((x,y+7,x+7,y+7),fill=1)
            d.point((x+2,y+5), fill=0)
    for x in (112,143):
        d.line((x,40,x,71),fill=0)
    d.line((112,40,143,40),fill=0)
    # Two tied skiffs read as local boats rather than another walkable route.
    for x, y in ((82,48),(159,43)):
        d.polygon([(x,y),(x+14,y),(x+22,y+4),(x+15,y+8),(x+3,y+8)],fill=0)
        d.polygon([(x+2,y+2),(x+14,y+2),(x+19,y+4),(x+14,y+6),(x+4,y+6)],fill=3)
        d.line((x+7,y+3,x+7,y+5),fill=1)
        d.line((x+13,y+3,x+13,y+5),fill=1)

    def building(tx, ty, width, label):
        # Ridge, metal roofing, overhanging eave, and a timber shop front.
        # The footprint is shared with collision; no roof over a street.
        x,y=tx*8,ty*8
        end=x+width*8-1
        for row in range(ty,ty+4):
            slots[row][tx:tx+width] = [0]*width
        d.polygon([(x,y+8),(x+5,y+1),(end-5,y+1),(end,y+8),
                   (end,y+31),(x,y+31)],fill=0)
        d.polygon([(x+2,y+8),(x+6,y+2),(end-6,y+2),(end-2,y+8),
                   (end-2,y+14),(x+2,y+14)],fill=2)
        d.line((x+6,y+3,end-6,y+3),fill=3)
        for ix in range(x+8,end-3,8):
            d.line((ix,y+5,ix,y+14),fill=1)
        d.line((x+2,y+14,end-2,y+14),fill=3)
        d.rectangle((x+2,y+17,end-2,y+29),fill=1)
        for yy in (19,23,27):
            d.line((x+3,y+yy,end-3,y+yy),fill=2)
        mid=(x+end)//2
        d.rectangle((mid-7,y+23,mid+7,y+30),fill=0)
        d.line((mid-6,y+26,mid+6,y+26),fill=2)
        d.line((mid-6,y+28,mid+6,y+28),fill=2)
        d.rectangle((mid-13,y+16,mid+13,y+22),fill=0)
        text(idx,label,mid,y+17)
        for xx in (x+4,end-11):
            d.rectangle((xx,y+22,xx+7,y+27),fill=0)
            d.rectangle((xx+1,y+23,xx+6,y+26),fill=2)
            d.line((xx+1,y+23,xx+6,y+23),fill=3)
            d.line((xx+3,y+23,xx+3,y+26),fill=1)

    for tx, ty, width, label in BUILDINGS:
        building(tx, ty, width, label)

    def planter(tx,ty,width):
        # Walled beds and their repeated rows of pale new growth.
        for i in range(width):
            x,y=(tx+i)*8,ty*8
            d.rectangle((x,y+1,x+7,y+6),fill=0)
            d.rectangle((x,y+2,x+7,y+4),fill=2)
            d.line((x+1,y+5,x+6,y+5),fill=2)
            d.line((x+2,y+3,x+3,y+2),fill=3)
            d.point((x+5,y+3),fill=3)
            if i in (0,width-1):
                edge = x if i==0 else x+7
                d.line((edge,y+1,edge,y+6),fill=0)

    for box in PLANTERS:
        planter(*box)
    for y in (14,29,30):
        for x in (1,2,3,28,29,30):
            # Flat wildflowers leave the outer circulation lane open.
            px,py=x*8,y*8
            d.line((px+2,py+5,px+3,py+2),fill=2)
            d.point((px+3,py+2),fill=3)
            d.point((px+6,py+4),fill=3)

    # Put each flag-controlled lamp on the kiosk counter. A clipped work
    # order, two ink lines and the name header make the station readable.
    for name, _, slot, x, y in DISTRICTS:
        slots[y//8][x//8:x//8+4] = [0]*4
        slots[y//8+1][x//8:x//8+4] = [0,0,slot,0]
        d.rectangle((x,y,x+31,y+15),fill=0)
        d.line((x+1,y,x+30,y),fill=2)
        text(idx, name, x+16, y+2)
        d.rectangle((x+1,y+8,x+30,y+14),fill=1)
        d.line((x+1,y+15,x+30,y+15),fill=2)
        d.rectangle((x+5,y+8,x+12,y+13),fill=3)
        d.line((x+7,y+8,x+10,y+8),fill=2)
        d.line((x+7,y+10,x+10,y+10),fill=0)
        d.line((x+7,y+12,x+9,y+12),fill=1)
        d.rectangle((x+16,y+8,x+23,y+15),fill=0)
        d.rectangle((x+17,y+9,x+22,y+14),fill=1)
        d.rectangle((x+18,y+10,x+21,y+13),fill=3)

    # A brass compass set flat in the center square gives the crossing a
    # landmark without changing movement or hiding the player's feet.
    d.polygon([(127,165),(138,176),(127,187),(116,176)],outline=3)
    d.line((127,168,127,184),fill=2)
    d.line((119,176,135,176),fill=2)
    d.polygon([(127,168),(124,177),(127,175),(130,177)],fill=3)
    return idx, slots

def text(image,word,cx,y):
    """Render small district labels into the background, without runtime fonts."""
    font={
        'D':['110','101','101','101','110'],'T':['111','010','010','010','010'],
        'W':['101','101','111','111','101'],'K':['101','101','110','101','101'],
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
    # Tile-aligned footprints leave clear approaches to all kiosk triggers.
    for y in range(H):
        for x in range(W):
            if x in (0,W-1) or y < 3 or y == H-1: grid[y][x] = 15
            if 2 <= y <= 8: grid[y][x] = 15
    for y in range(6, 9):
        for x in range(14, 18):
            grid[y][x] = 0
    for tx, ty, width, _ in BUILDINGS:
        for y in range(ty, ty+4):
            for x in range(tx, tx+width):
                grid[y][x] = 15
    for tx, ty, width in PLANTERS:
        for x in range(tx, tx+width):
            grid[ty][x] = 15
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
        depart=[set_near(0,'leave-zone-'+str(n)),remove_a,
                ticket.fade_out('hub:fade-'+str(n)),
                ticket.switch_scene(target['scene_id'],*target['start'],'right','hub:job-'+str(n))]
        accept=[ticket.dialogue(target['pages'],'hub:accept-'+str(n)),
                ev('EVENT_CHOICE', {'variable':'L0','trueText':'Accept job',
                   'falseText':'Keep exploring'}, 'choose-'+str(n)),
                ticket.if_value('L0',1,'hub:accepted-'+str(n),depart,[])]
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
    return storm_worker_topdown.frames()

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
