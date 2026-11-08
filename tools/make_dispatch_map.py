"""Author one dispatch state and an isolated playable copy, never production scenes.

Managed Python: tools/make_dispatch_map.py [--unlit]
Default seed is earned-looking Amara completion for the WO-0413 prototype only.
--unlit creates the same state with home0=0 to test real flag-driven lighting.
These diagnostic seeds are not campaign evidence. All production cards stay as-is.
"""
from pathlib import Path
import argparse
from PIL import Image, ImageDraw
import dispatch_map as contract
import intro
import make_intro_scene as cinematic
import make_ticket_scene as ticket_scene
import make_climb_scene as shared
from make_campaign_diagnostics import fixture, seed

ROOT = Path(__file__).resolve().parent.parent
# Deliberate native 3x5 lettering. Background pixels, so no runtime font VRAM.
FONT = {
 'A':['010','101','111','101','101'], 'E':['111','100','110','100','111'],
 'H':['101','101','111','101','101'], 'I':['111','010','010','010','111'],
 'M':['101','111','111','101','101'], 'N':['101','111','111','111','101'],
 'O':['010','101','101','101','010'], 'P':['110','101','110','100','100'],
 'R':['110','101','110','101','101'], 'S':['011','100','010','001','110'],
 'T':['111','010','010','010','010'], 'X':['101','101','010','101','101'],
 'Y':['101','101','010','010','010'], 'L':['100','100','100','100','111'],
 ':':['0','1','0','1','0'], ' ':['0']*5,
}

def build_art():
    idx = Image.new('L', (160,144), 0)
    slots = [[0]*20 for _ in range(18)]
    d = ImageDraw.Draw(idx)
    def region(x0,y0,x1,y1,slot):
        for y in range(y0,y1+1):
            for x in range(x0,x1+1): slots[y][x]=slot
    def text(word,cx,y):
        width=sum(len(FONT[c][0])+1 for c in word)-1
        x=cx-width//2
        for c in word:
            for yy,row in enumerate(FONT[c]):
                for xx,v in enumerate(row):
                    if v=='1': d.point((x+xx,y+yy),fill=3)
            x+=len(FONT[c][0])+1
    region(0,2,19,13,1)
    d.rectangle((0,16,159,111),fill=1)
    # Quiet contoured ground with a shared crew route, no decorative hazard cues.
    d.line([(0,57),(52,57),(64,60),(96,60),(108,57),(159,57)],fill=2,width=2)
    d.line([(80,58),(80,108),(159,108)],fill=2,width=3)
    d.line([(0,108),(80,108)],fill=2,width=3)
    for x,y in [(8,66),(48,92),(144,64),(56,26),(8,96),(144,100)]:
        d.line((x,y,x+3,y),fill=2);d.point((x+1,y-1),fill=3)
    text('NEXT: HIROSHI',80,5)
    for name,variable,slot,x,y in contract.HOMES:
        # Aligned tile bands isolate names, architecture and each home's window.
        region(x//8,y//8,(x+31)//8,(y+31)//8,2)
        region(x//8,(y-8)//8,(x+31)//8,(y-1)//8,0)
        d.rectangle((x,y-8,x+31,y-1),fill=0)
        text(name,x+16,y-6)
        d.rectangle((x,y,x+31,y+31),fill=0)
        d.polygon([(x,y+11),(x+15,y),(x+31,y+11)],fill=2)
        d.line([(x+1,y+11),(x+15,y+1),(x+30,y+11)],fill=3)
        d.rectangle((x+3,y+12,x+28,y+30),fill=2)
        d.line((x+3,y+13,x+28,y+13),fill=3)
        d.rectangle((x+5,y+17,x+12,y+27),fill=1)
        d.point((x+10,y+22),fill=3)
        region(x//8+2,y//8+2,x//8+2,y//8+2,slot)
        d.rectangle((x+16,y+16,x+23,y+23),fill=0)
        d.rectangle((x+17,y+17,x+22,y+22),fill=3)
        d.line((x+19,y+17,x+19,y+22),fill=1)
        d.line((x+17,y+20,x+22,y+20),fill=1)
        d.line((x+2,y+31,x+29,y+31),fill=1)
    # Single current-job arrow, independent of completion lights.
    region(12,4,13,5,0)
    d.rectangle((96,32,111,47),fill=0)
    d.line((98,40,107,40),fill=3,width=2)
    d.polygon([(106,36),(111,40),(106,44)],fill=3)
    for y in range(14,18): slots[y]=[7]*20
    return idx,slots


def write_art():
    idx,slots=build_art()
    bg=ROOT/'assets/backgrounds'/f'{contract.BACKGROUND_NAME}.png'
    proxy=idx.point([255,170,85,0]+[0]*252).convert('RGB')
    proxy.save(bg, optimize=False)
    shared.write_json(Path(str(bg)+'.gbsres'), {
        '_resourceType':'background','id':contract.BACKGROUND_ID,
        'name':contract.BACKGROUND_NAME,'symbol':'bg_'+contract.BACKGROUND_NAME,
        'filename':bg.name,'width':20,'height':18,'imageWidth':160,'imageHeight':144,
        'autoColor':False,'tileColors':shared.collision_rle(slots,20,18)})
    for name,colors in contract.PALETTES.items():
        shared.write_json(ROOT/'project/palettes'/f'dispatch_{name}.gbsres', {
            '_resourceType':'palette','id':contract.palette_id(name),
            'name':'Dispatch '+name,'colors':colors})
    return idx,slots


def prototype_scene():
    scene=ticket_scene.scene_resource(contract.tickets.WORK_ORDER_SCENE_ID,
        'work_order', 'Dispatch Map Prototype', 0, 720, -240, [])
    scene['backgroundId']=contract.BACKGROUND_ID
    scene['paletteIds']=contract.PALETTE_IDS
    script=ticket_scene.setup('dispatch-prototype')
    script.append(ticket_scene.ev('EVENT_OVERLAY_SET_SCANLINE_CUTOFF',
                  {'units':'pixels','y':shared.number(150)},'dispatch:cutoff'))
    for name,variable,slot,x,y in contract.HOMES:
        def palette(state):
            args={f'palette{i}':'keep' for i in range(8)}
            args[f'palette{slot}']=contract.palette_id(state)
            return ticket_scene.ev('EVENT_PALETTE_SET_BACKGROUND',args,f'dispatch:{name}:{state}')
        script.append(ticket_scene.if_value(variable,1,f'dispatch:{name}:home',
                                            [palette('on')],[palette('off')]))
    # One A-confirmation replaces the card's three-page pause in this prototype.
    ticket=contract.tickets.TICKETS[contract.PROTOTYPE_TICKET]
    script += [ticket_scene.ev('EVENT_TEXT_SET_ANIMATION_SPEED',
                  {'speedIn':0,'speedOut':0,'speed':0,'allowFastForward':True},'dispatch:text-instant'),
               ticket_scene.dialogue(contract.PAGES,'dispatch:order'),
               ticket_scene.ev('EVENT_TEXT_SET_ANIMATION_SPEED',
                  {'speedIn':0,'speedOut':0,'speed':1,'allowFastForward':True},'dispatch:text-restore'),
               ticket_scene.fade_out('dispatch:fade'),
               ticket_scene.switch_scene(ticket['scene_id'],*ticket['start'],'right','dispatch:to-job')]
    scene['script']=script
    return scene


def write_prototype(unlit=False):
    write_art()
    values={'0':0 if unlit else 1,'9':0,'11':0,'13':0,'16':2}
    destination=fixture('dispatch-map-unlit' if unlit else 'dispatch-map','work_order',0,0,values)
    path=destination/'project/scenes/work_order/scene.gbsres'
    scene=prototype_scene();scene['script']=seed(values)+scene['script']
    shared.write_json(path,scene)
    actor=cinematic.actor_resource(index=0,symbol='dispatch_neighborhood_hero',
            name='Neighborhood Hero',key='dispatch-neighborhood-hero',
            sprite_id=intro.NEIGHBORHOOD_HERO_SPRITE_ID,x=10,y=6,direction='right',
            start_script=[cinematic.actor_state('$self$','Idle','dispatch:hero-idle'),
                cinematic.ev('EVENT_ACTOR_COLLISIONS_DISABLE',{'actorId':'$self$'},'dispatch:hero-safe')])
    actor['animate']=False
    shared.write_json(path.parent/'actors/dispatch_hero.gbsres',actor)
    print('One WO-0413 prototype:',destination/'mr-cfe.gbsproj')
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unlit',action='store_true')
    args=parser.parse_args()
    write_prototype(args.unlit)
