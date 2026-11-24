# Will be deprecating this module in the future

BORDER_STANDARD = {"TOP": "=", "BOTTOM": "=", "LEFT": " ", "RIGHT": " "}
BORDER_PANE = {"TOP": "=", "BOTTOM": "=", "LEFT": "|", "RIGHT": "|"}
BORDER_V4L1D8R = {"TOP": "<>", "BOTTOM": "<>", "LEFT": "||", "RIGHT": "||"}

def get_border_pattern(name: str = "standard"):
    return dict({
        "standard": BORDER_STANDARD,
        "pane": BORDER_PANE,
        "v4l1d8r": BORDER_V4L1D8R,
    }.get(name.lower(), BORDER_STANDARD))
