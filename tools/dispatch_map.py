"""One-state WO-0413 map contract; expansion waits for playable approval."""
import tickets
import intro

BACKGROUND_NAME = 'dispatch_neighborhood'
BACKGROUND_ID = tickets.resource_id('background:dispatch-neighborhood')
PROTOTYPE_TICKET = 2
# Household completion is independent of transient ticket16.
HOMES = (('AMARA', '0', 3, 16, 24), ('HIROSHI', '9', 4, 112, 24),
         ('PRIYA', '11', 5, 16, 72), ('EMIL', '13', 6, 112, 72))
PALETTES = {
    'ink': intro.UI,
    'ground': ['0B101E', '182D30', '35524B', '799887'],
    'house': ['0B101E', '392B32', '765552', 'BB9479'],
    'off': ['392B32', '765552', '233442', '526374'],
    'on': ['392B32', '765552', 'D89B4B', 'FFE7A0'],
}

def palette_id(name):
    return tickets.resource_id('palette:dispatch-' + name)

PALETTE_IDS = [palette_id(n) for n in ('ink', 'ground', 'house', 'off', 'off', 'off', 'off')] + ['default-ui']
PAGES = ['WO-0413  HIROSHI\nOxygen is off\nA: take the job']
