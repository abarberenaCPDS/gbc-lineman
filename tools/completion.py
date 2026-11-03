"""Source contract for the short household-completion reward sting."""

import uuid

import make_sfx


NAME = "home_complete"
RESOURCE_ID = str(uuid.uuid5(make_sfx.NS, f"sound/{NAME}"))

# A compact E5-G5-B5 arpeggio. The modest gaps let the three pitches read as
# one resolved milestone while keeping the feedback below the 300 ms budget.
SEGMENTS = [
    ("square", 659, 659, 0.052, 0.42),
    ("silence", 0, 0, 0.012, 0.0),
    ("square", 784, 784, 0.052, 0.44),
    ("silence", 0, 0, 0.012, 0.0),
    ("square", 988, 988, 0.090, 0.46),
]


def sound_id():
    """Return the stable GB Studio resource id for this sound."""
    return RESOURCE_ID


def synth():
    """Render the deterministic WAV bytes using the shared project synth."""
    return make_sfx.synth(SEGMENTS)
