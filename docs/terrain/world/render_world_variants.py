"""Render planning diagrams, not game assets or collision geometry."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
O=Path(__file__).resolve().parent
F='/System/Library/Fonts/Supplemental/Arial.ttf'
INK='#e1edf0'; MUT='#a9bec8'; GREEN='#73d4bb'; GOLD='#f5c479'; BG='#101c24'
def font(n):return ImageFont.truetype(F,n)
def text(x,y,s,n=22,c=INK):d.text((x,y),s,font=font(n),fill=c)
def base(title,subtitle):
 global im,d
 im=Image.new('RGB',(1440,1020),BG);d=ImageDraw.Draw(im)
 text(40,25,title,34);text(40,76,subtitle,22,GREEN)
 d.rounded_rectangle((30,120,1410,680),18,outline='#3b5562',width=2)
 # Mountain skyline gives context without claiming a real location.
 d.polygon([(55,365),(220,145),(390,340),(560,165),(725,345),(925,150),(1100,340),(1270,170),(1385,350)],fill='#1d303b')
 text(55,641,'WORLD ROUTES — schematic geography, not a real Big Bear map',18,MUT)
def node(x,y,title,lines,color=GREEN,w=270):
 d.rounded_rectangle((x,y,x+w,y+105),12,fill='#1a2c36',outline=color,width=3)
 size=24
 while d.textlength(title,font=font(size))>w-28:size-=1
 text(x+14,y+10,title,size,color)
 for i,l in enumerate(lines):
  size=19
  while d.textlength(l,font=font(size))>w-28:size-=1
  text(x+14,y+45+i*25,l,size)
def path(points,color=GREEN,width=5):
 d.line(points,fill=color,width=width)
 x,y=points[-1];px,py=points[-2];import math
 a=math.atan2(y-py,x-px);q=12
 d.polygon([(x,y),(x-q*math.cos(a-.45),y-q*math.sin(a-.45)),(x-q*math.cos(a+.45),y-q*math.sin(a+.45))],fill=color)
def notes(rows,foot):
 for i,(head,body) in enumerate(rows):
  yy=710+i*79;text(50,yy,head,24,GOLD);text(50,yy+32,body,21)
 text(45,973,foot,19,MUT)
def save(name):im.save(O/name)
base('1 / LAKESIDE NEIGHBORHOOD','A walkable town hub with four distinct repair routes • Recommended starting direction')
d.ellipse((520,420,900,625),fill='#214b5e');text(660,574,'LAKE',22,'#91bdcb')
for end in [(350,300),(1060,260),(355,485),(1070,480)]:path([(720,397),end])
node(570,335,'TOWN / UTILITY YARD',['Take job • see lights return','Walk to a signed trailhead'],w=310)
node(90,225,'1  AMARA / CABINS',['Forest steps + short jumps','Clear route to the first home'])
node(1050,180,'2  HIROSHI / RIDGE',['Open wind + landing choices','Working pads between crossings'])
node(90,450,'3  PRIYA / CREEK',['Descend toward the visible goal','Broken footbridges + repair'])
node(1050,440,'4  EMIL / LOOKOUT',['Foreshadow the climb, then rise','Rim crossing + dinner payoff'])
text(545,145,'Cabins • pines • lake views • service trails',22,MUT)
notes([('Campaign rhythm','Intro job → town → Amara → town → Hiroshi → town → Priya → town → Emil → restored town.'),('Gameplay identity','Each route has its own terrain skill. Quick return paths let restoration punctuate the harder jobs.'),('Tradeoff','Strong orientation and visible progress; the repeated hub return can feel formulaic if it takes too long.')], 'Main jobs retain five repairs each. Route order shown is progression, not a claim that all four are open at once.')
save('01-lakeside-neighborhood.png')
base('2 / THE VALLEY RESTORATION LOOP','One connected journey around the mountain community • Shortcuts reconnect the town')
d.ellipse((475,290,935,580),fill='#214b5e');text(640,417,'RESERVOIR',24,'#91bdcb')
path([(360,530),(210,330),(430,235),(820,235),(1180,360),(1180,520),(900,580),(555,580),(360,530)])
node(75,470,'TOWN / START + RETURN',['Intro beside the utility depot','Final circuit returns here'])
node(100,205,'1  AMARA / LOWER ROAD',['Climb past hillside cabins','First restored section'])
node(650,165,'2  HIROSHI / HIGH PASS',['Exposed ridge crossing','View the creek route below'])
node(1050,325,'3  PRIYA / CREEK',['Descend from the high pass','Repair along the watercourse'])
node(685,505,'4  EMIL / RETURN RIDGE',['Climb to the last connection','Return toward the lit town'])
# Central shortcut label distinct from primary progression.
text(515,605,'Repairs open short return paths',20,GOLD)
notes([('Campaign rhythm','Intro → Amara → Hiroshi → Priya → Emil → town. Each destination points toward the next one.'),('Gameplay identity','The landscape carries the story: ascend the pass, descend into the creek, then close the circuit.'),('Tradeoff','Strong expedition feel; needs more boundary work and reliable shortcuts to avoid long cable-recovery walks.')], 'The town remains walkable. Side paths become convenient after repair; avoid mandatory repeated laps.')
save('02-valley-loop.png')
base('3 / THE MOUNTAIN SPINE','A central service trail with terraced neighborhoods • Height becomes the campaign landmark')
path([(680,595),(680,500),(865,375),(865,300),(1010,215)])
path([(840,365),(380,400)]);path([(380,505),(680,530)],GOLD,4)
node(550,530,'TOWN / VALLEY FLOOR',['Intro repair + walkable hub','Look up toward the dark summit'])
node(505,400,'1  AMARA / LOWER PINES',['Short ledges teach the climb','First visible lights below'])
node(865,270,'2  HIROSHI / WIND SHELF',['Exposed traverse across height','Sheltered work pads, open sky'])
node(90,365,'3  PRIYA / RAVINE',['Branch downward into the creek','A return path rejoins the spine'])
node(1000,135,'4  EMIL / UPPER RIM',['Sustained, varied ascent','Final overlook of restored homes'])
text(75,565,'Side branch breaks the climb rhythm.',21,GOLD)
notes([('Campaign rhythm','Intro → lower cabins → wind shelf → creek detour → upper rim → short return to the town.'),('Gameplay identity','Vertical progress is always legible. Changing views show how far the community has recovered.'),('Tradeoff','Strong mountain identity; risks too much climbing and confusing camera transitions unless the creek breaks it up.')], 'Keep the liked jump physics. Stage scene exits and arrivals as one continuous mountain, not unrelated rooms.')
save('03-mountain-spine.png')
# Tutorial overview, six cards in two rows.
base('SHARED INTRO JOB / RESTORE THE TRAILHEAD LIGHT','After Press Start • Expand Service Opening into a short learn-by-doing mission')
steps=[('1  WALK + LOOK',['A dark streetlight is visible.','Walk toward its broken line.'],(65,165)),('2  JUMP + LAND',['A small step, then a wider gap.','Tap or hold A; safe floor below.'],(545,165)),('3  PICK UP',['Press B at the snapped pole.','Carry pose makes the cable clear.'],(1025,165)),('4  REPAIR + SEE',['Press B at the matching box.','Light returns; checkpoint earned.'],(65,425)),('5  READ THE WIND',['See warning → burst → calm.','Cross from a safe waiting spot.'],(545,425)),('6  GO TO TOWN',['A short route needs no new hint.','Meet the next job at the hub.'],(1025,425))]
for title,lines,(x,y) in steps:node(x,y,title,lines,w=345)
path([(410,218),(540,218)]);path([(890,218),(1020,218)])
path([(1195,275),(1195,360),(235,360),(235,420)])
path([(410,478),(540,478)]);path([(890,478),(1020,478)])
notes([('A real job, not a lecture','Aim for roughly 2–3 minutes on a first try. One small repair powers a useful landmark and opens the town.'),('Failure teaches safely','No forced hit. If shocked, return nearby, explain the dropped cable once, and let the player retry quickly.'),('Teach the rest where it matters','Introduce whipping wires, cracked boards and hidden-cable warnings in their first meaningful mission encounters.')], 'Proposed pacing only. Tutorial repair is separate from the existing twenty household repairs; controls shown are cartridge A/B.')
save('04-intro-job.png')
