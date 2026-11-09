"""Town cels for Storm Worker; the platformer generator owns his profile."""

from PIL import ImageDraw

from make_opening_characters import PROXY, TRANSPARENT, _worker_frame


def _rows(image):
    shades = {TRANSPARENT: ".", **{PROXY[i]: str(i) for i in (1, 2, 3)}}
    return tuple("".join(shades[image.getpixel((x, y))] for x in range(16))
                 for y in range(32))


def _vertical(facing, step=0):
    # Draw in local coordinates over the 24px body. The helmet and shoulders
    # stay level in the gait; only the opposed arms and planted foot change.
    image = _worker_frame(24, "idle", "right")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 8, 15, 31), fill=TRANSPARENT)

    def box(x1, y1, x2, y2, shade):
        draw.rectangle((x1, 8+y1, x2, 8+y2), fill=PROXY[shade])

    def poly(points, shade):
        draw.polygon([(x, y+8) for x, y in points], fill=PROXY[shade])

    front = facing == "down"
    # Rounded dome and wide brim. From behind, the cream rear shell sits
    # above the dark nape; from the front, the eyes sit under the brim.
    poly(((5,0),(10,0),(12,2),(12,3),(13,3),(13,5),(2,5),
          (2,3),(3,3),(3,2)), 3)
    box(5,1,10,1,1)
    box(4,2,11,3,1)
    box(3,4,12,4,1)
    if front:
        box(4,6,11,7,3)
        box(5,5,10,7,1)
        box(5,6,5,6,3)
        box(10,6,10,6,3)
        box(6,8,9,8,3)
    else:
        box(4,5,11,6,3)
        box(5,5,10,5,1)
        box(6,7,9,8,3)
        box(7,7,8,7,2)

    # Arms have their own seams. A short elbow swing is enough at 24px.
    for side, x in ((-1, 2), (1, 11)):
        end = 16 + side*step
        box(x,10,x+2,end,3)
        box(x+1,11,x+1,end-1,2)
        box(x+1,end-2,x+1,end-2,1)
        box(x+1,end,x+1,end,1)

    poly(((5,8),(10,8),(12,9),(12,15),(11,17),(4,17),(3,15),(3,9)), 3)
    poly(((5,9),(10,9),(11,10),(11,15),(10,16),(5,16),(4,15),(4,10)), 2)
    box(4,12,11,13,1)
    if front:
        box(7,9,7,11,3)
        box(7,14,7,16,3)
        box(7,17,8,17,1)
        box(4,17,5,18,2)
    else:
        # Clean uninterrupted stripe across the back and a small yoke seam.
        box(6,10,9,10,3)
        box(10,17,11,18,2)

    for side, x in ((-1, 4), (1, 8)):
        toe = 23 - int(side*step < 0)
        box(x+1,18,x+3,toe-1,3)
        box(x+1,19,x+2,20,2)
        box(x, toe-2, x+3, toe, 3)
        # The front shows toe caps; the rear shows the heel one row higher.
        highlight = toe-1 if front else toe-2
        box(x+1, highlight, x+2, highlight, 2)
    return _rows(image)


def frames():
    right = [_rows(_worker_frame(24, "idle", "right")),
             *[_rows(_worker_frame(24, "walk", "right", phase)) for phase in (1, 3)]]
    left = [tuple(row[::-1] for row in frame) for frame in right]
    return right + left + [_vertical(facing, step)
                           for facing in ("up", "down") for step in (0, -1, 1)]
