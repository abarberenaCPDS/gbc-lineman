"""Walkable hub source contracts; native movement/playability still needs ROM tests."""
from collections import deque
import unittest
import make_dispatch_hub as hub
import make_ticket_scene as tickets
from make_opening_characters import _worker_frame

class DispatchHubTests(unittest.TestCase):
    def test_all_district_trailheads_reachable_around_solid_lake(self):
        grid=hub.collision_grid(); start=hub.START
        seen={start};todo=deque([start])
        while todo:
            x,y=todo.popleft()
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                p=(x+dx,y+dy)
                # Player occupies two horizontal cells; keep both clear.
                if 0<=p[0]<hub.W-1 and 0<=p[1]<hub.H and p not in seen and not any(grid[p[1]][p[0]+k] for k in (0,1)):
                    seen.add(p);todo.append(p)
        for y in range(2,9):
            for x in range(hub.W):
                self.assertEqual(not grid[y][x], 6 <= y <= 8 and 14 <= x < 18)
        self.assertIn((15,6),seen)   # Walkable pier
        self.assertIn((15,28),seen)  # Southern green
        for x,y,width,_ in hub.BUILDINGS:
            self.assertTrue(all(grid[yy][xx] for yy in range(y,y+4) for xx in range(x,x+width)))
        for x,y,width in hub.PLANTERS:
            self.assertTrue(all(grid[y][xx] for xx in range(x,x+width)))
        for trigger in hub.build_triggers():
            self.assertIn((trigger['x']+1,trigger['y']+1),seen)
        self.assertEqual(len(hub.build_triggers()),4)

    def test_job_requires_intentional_input_and_only_next_job_can_start(self):
        scene=hub.build_scene()
        self.assertFalse(any(e['command']=='EVENT_TEXT' for e in scene['script']))
        input_event=scene['script'][-1]
        self.assertEqual(input_event['args'],{'input':['a'],'override':True})
        switches=[e for e in tickets.walk([input_event]) if e['command']=='EVENT_SWITCH_SCENE']
        self.assertEqual(len(switches),4)
        self.assertEqual({e['args']['sceneId'] for e in switches},
                         {t['scene_id'] for t in hub.contract.tickets.TICKETS.values()})
        gates=[e for e in tickets.walk([input_event]) if e['command']=='EVENT_IF' and
               e['args']['condition']['valueA'].get('value')=='16']
        self.assertTrue(all(any(e['command']=='EVENT_SWITCH_SCENE' for e in tickets.walk(g['children']['true']))
                            for g in gates if any(e['command']=='EVENT_SWITCH_SCENE' for e in tickets.walk([g]))))
        writes=[e['args']['variable'] for e in tickets.walk(scene['script']) if e['command']=='EVENT_SET_VALUE']
        self.assertEqual(set(writes),{'27'})
        self.assertFalse(any(e['command']=='EVENT_SET_VALUE' and e['args']['variable'] in ('0','9','11','13','16','56')
                             for e in tickets.walk(scene['script'])))
        removes=[e for e in tickets.walk([input_event]) if e['command']=='EVENT_REMOVE_INPUT_SCRIPT']
        self.assertEqual(len(removes),4)
        self.assertTrue(all(e['args']['input']==['a'] for e in removes))
        choices=[e for e in tickets.walk([input_event]) if e['command']=='EVENT_CHOICE']
        self.assertEqual(len(choices),4)
        self.assertTrue(all(e['args']=={'variable':'L0','trueText':'Accept job',
                                       'falseText':'Keep exploring'} for e in choices))
        confirmations=[e for e in tickets.walk([input_event]) if e['command']=='EVENT_IF' and
                       e['args']['condition']['valueA'].get('value')=='L0']
        self.assertEqual(len(confirmations),4)
        for confirmation in confirmations:
            self.assertEqual(confirmation['children']['false'],[])
            self.assertTrue(any(e['command']=='EVENT_SWITCH_SCENE'
                                for e in confirmation['children']['true']))
        for trigger in hub.build_triggers():
            self.assertEqual(trigger['leaveScript'][0]['args']['value']['value'],0)

    def test_windows_still_use_real_completion_flags(self):
        scene=hub.build_scene()
        flags=[e['args']['condition']['valueA']['value'] for e in scene['script'] if e['command']=='EVENT_IF']
        self.assertEqual(flags,['0','9','11','13'])
        image,slots=hub.build_art()
        self.assertEqual(image.size,(256,256))
        for _,_,slot,x,y in hub.DISTRICTS:
            self.assertEqual(slots[(y+8)//8][(x+16)//8],slot)
            self.assertEqual(sum(row.count(slot) for row in slots),1)
        tiles={image.crop((x*8,y*8,x*8+8,y*8+8)).tobytes() for y in range(hub.H) for x in range(hub.W)}
        self.assertLess(len(tiles),192)
        self.assertEqual(scene['paletteIds'][2],hub.WATER_PALETTE_ID)
        self.assertEqual(scene['paletteIds'][-1],'default-ui')
        self.assertEqual(scene['name'],'Lakeside Town')
        # Four district signposts replace the previous duplicated homes.
        self.assertNotIn('door:',str(hub.build_triggers()))

    def test_seed_and_help_are_once_only(self):
        scene=hub.fixture_scene({'0':1,'9':0,'11':0,'13':0,'16':2})
        seed_gate=scene['script'][0];help_gate=scene['script'][-1]
        self.assertEqual(seed_gate['args']['condition']['valueA']['value'],'56')
        self.assertEqual(seed_gate['args']['condition']['valueB']['value'],0)
        self.assertEqual(seed_gate['children']['false'],[])
        self.assertEqual(help_gate['args']['condition']['valueB']['value'],1)
        self.assertEqual(help_gate['children']['true'][-1]['args']['value']['value'],2)
        self.assertEqual(help_gate['children']['false'],[])

    def test_production_scene_has_only_real_gates_and_ticket_accept_pages(self):
        events=list(tickets.walk(hub.build_scene()['script']))
        gates=[e for e in events if e['command']=='EVENT_IF' and
               e['args']['condition']['valueA'].get('value') in ('0','9','11','13')]
        self.assertEqual(len(gates),8)
        text_pages=[e['args']['text'] for e in events if e['command']=='EVENT_TEXT']
        self.assertTrue(all(ticket['pages'] in text_pages for ticket in hub.contract.tickets.TICKETS.values()))
        speed=[e for e in events if e['command']=='EVENT_ACTOR_SET_MOVEMENT_SPEED']
        self.assertEqual([e['args']['speed'] for e in speed],[1])

    def test_directional_derivative_preserves_accepted_side_frames(self):
        frames=hub.hero_frames();sheet,meta=hub.build_hero()
        native_poses = (_worker_frame(24, "idle", "right"),
                        _worker_frame(24, "walk", "right", 1),
                        _worker_frame(24, "walk", "right", 3))
        for i,native in enumerate(native_poses):
            self.assertEqual(sheet.crop((i*16,0,i*16+16,32)).convert("RGB").tobytes(),
                             native.tobytes())
        for i in range(3):
            self.assertEqual(frames[i+3],tuple(row[::-1] for row in frames[i]))
        self.assertNotEqual(frames[6],frames[9])
        for group in (frames[6:9],frames[9:12]):
            self.assertEqual(len(set(group)),3)
            self.assertTrue(all(frame[8:16]==group[0][8:16] for frame in group))
            self.assertTrue(all(frame[-1]!='.'*16 for frame in group))
        self.assertEqual(meta['states'][0]['animationType'],'multi_movement')
        self.assertEqual([len(a['frames']) for a in meta['states'][0]['animations']],[1]*4+[4]*4)
        self.assertEqual((meta['boundsY'],meta['boundsHeight']),(0,8))
        self.assertLess(meta['numTiles'],64)
        self.assertTrue(all(len(f)==32 and all(len(r)==16 for r in f) for f in frames))
        self.assertTrue(all(len(frame['tiles'])==4 for anim in meta['states'][0]['animations'] for frame in anim['frames']))

    def test_dialogue_fits_native_width(self):
        for event in tickets.walk(hub.build_scene()['script']):
            if event['command']=='EVENT_TEXT':
                text=event['args']['text']
                if isinstance(text,str):text=[text]
                self.assertTrue(all(len(line)<=17 for page in text for line in page.split('\n')))

if __name__=='__main__': unittest.main()
