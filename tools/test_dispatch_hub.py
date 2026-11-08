"""Walkable hub source contracts; native movement/playability still needs ROM tests."""
from collections import deque
import unittest
import make_dispatch_hub as hub
import make_ticket_scene as tickets
import neighborhood_hero

class DispatchHubTests(unittest.TestCase):
    def test_all_doorsteps_reachable_without_crossing_houses(self):
        grid=hub.collision_grid(); start=hub.START
        seen={start};todo=deque([start])
        while todo:
            x,y=todo.popleft()
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                p=(x+dx,y+dy)
                # Player occupies two horizontal cells; keep both clear.
                if 0<=p[0]<hub.W-1 and 0<=p[1]<hub.H and p not in seen and not any(grid[p[1]][p[0]+k] for k in (0,1)):
                    seen.add(p);todo.append(p)
        for trigger in hub.build_triggers():
            self.assertIn((trigger['x']+1,trigger['y']+1),seen)
        self.assertTrue(all(grid[y//8+1][x//8+1] for _,_,_,x,y in hub.HOMES))

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
        for trigger in hub.build_triggers():
            self.assertEqual(trigger['leaveScript'][0]['args']['value']['value'],0)

    def test_windows_still_use_real_completion_flags(self):
        scene=hub.build_scene()
        flags=[e['args']['condition']['valueA']['value'] for e in scene['script'] if e['command']=='EVENT_IF']
        self.assertEqual(flags,['0','9','11','13'])
        image,slots=hub.build_art()
        self.assertEqual(image.size,(256,256))
        for _,_,slot,x,y in hub.HOMES:
            cells=[(xx,yy) for yy,row in enumerate(slots) for xx,v in enumerate(row) if v==slot]
            self.assertEqual(cells,[(x//8+2,y//8+2)])
        tiles={image.crop((x*8,y*8,x*8+8,y*8+8)).tobytes() for y in range(hub.H) for x in range(hub.W)}
        self.assertLess(len(tiles),192)
        self.assertEqual(scene['paletteIds'][-1],'default-ui')

    def test_seed_and_help_are_once_only(self):
        scene=hub.fixture_scene({'0':1,'9':0,'11':0,'13':0,'16':2})
        seed_gate=scene['script'][0];help_gate=scene['script'][-1]
        self.assertEqual(seed_gate['args']['condition']['valueA']['value'],'56')
        self.assertEqual(seed_gate['args']['condition']['valueB']['value'],0)
        self.assertEqual(seed_gate['children']['false'],[])
        self.assertEqual(help_gate['args']['condition']['valueB']['value'],1)
        self.assertEqual(help_gate['children']['true'][-1]['args']['value']['value'],2)
        self.assertEqual(help_gate['children']['false'],[])

    def test_directional_derivative_preserves_accepted_side_frames(self):
        frames=hub.hero_frames();sheet,meta=hub.build_hero()
        self.assertEqual(frames[0],neighborhood_hero.NEIGHBORHOOD_FRAMES[0])
        self.assertEqual(frames[1],neighborhood_hero.NEIGHBORHOOD_FRAMES[2])
        self.assertEqual(frames[2],neighborhood_hero.NEIGHBORHOOD_FRAMES[4])
        self.assertNotEqual(frames[6],frames[9])
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
