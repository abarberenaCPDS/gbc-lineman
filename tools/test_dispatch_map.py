"""Prototype boundaries and native layout/state contracts (no production writes)."""
import unittest
import dispatch_map as contract
import make_dispatch_map as generator
import make_ticket_scene as tickets
import intro

class DispatchMapTests(unittest.TestCase):
    def test_home_lights_use_completion_not_dispatch(self):
        scene=generator.prototype_scene()
        homes=[e for e in scene['script'] if e['command']=='EVENT_IF']
        self.assertEqual([e['args']['condition']['valueA']['value'] for e in homes],['0','9','11','13'])
        for event,home in zip(homes,contract.HOMES):
            for branch,state in [('true','on'),('false','off')]:
                args=event['children'][branch][0]['args']
                self.assertEqual(args[f'palette{home[2]}'],contract.palette_id(state))
                self.assertTrue(all(v=='keep' for k,v in args.items() if k!=f'palette{home[2]}'))

    def test_one_confirmation_preserves_job_and_progress(self):
        script=generator.prototype_scene()['script']
        self.assertEqual(len([e for e in script if e['command']=='EVENT_TEXT']),1)
        self.assertFalse(any(e['command']=='EVENT_SET_VALUE' for e in tickets.walk(script)))
        switch=script[-1]['args'];target=contract.tickets.TICKETS[2]
        self.assertEqual(switch['sceneId'],target['scene_id'])
        self.assertEqual((switch['x']['value'],switch['y']['value']),target['start'])
        for page in contract.PAGES:
            self.assertLessEqual(len(page.split('\n')),3)
            self.assertTrue(all(len(line)<=17 for line in page.split('\n')))

    def test_each_light_owns_only_one_aligned_window_tile(self):
        idx,slots=generator.build_art()
        self.assertEqual(idx.size,(160,144))
        self.assertTrue(all(0<=v<=3 for v in idx.tobytes()))
        for _,_,slot,x,y in contract.HOMES:
            used=[(tx,ty) for ty,row in enumerate(slots) for tx,v in enumerate(row) if v==slot]
            self.assertEqual(used,[(x//8+2,y//8+2)])
        self.assertTrue(all(v==7 for row in slots[14:] for v in row))

    def test_native_map_is_compact_and_ui_slot_reserved(self):
        idx,slots=generator.build_art()
        tiles={tuple(idx.crop((x*8,y*8,x*8+8,y*8+8)).tobytes()) for y in range(18) for x in range(20)}
        self.assertLess(len(tiles),100)
        self.assertEqual(contract.PALETTE_IDS[-1],'default-ui')
        scene=generator.prototype_scene()
        self.assertEqual(scene['type'],'TOPDOWN')
        self.assertEqual(scene['id'],contract.tickets.WORK_ORDER_SCENE_ID)
        self.assertEqual(tickets.build_scenes()['work_order']['backgroundId'],contract.tickets.BACKGROUND_ID)
        self.assertEqual(tickets.build_scenes()['storm_report']['backgroundId'],contract.tickets.BACKGROUND_ID)

if __name__=='__main__': unittest.main()
