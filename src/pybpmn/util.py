import json
import re
from pathlib import Path
from typing import Tuple

# noinspection PyProtectedMember
from lxml.etree import _Element as Element
from yamlu.img import BoundingBox


def capitalize_fc(s: str):
    return s[0].upper() + s[1:]


def split_camel_case(name: str) -> str:
    # e.g. "timerStartEvent" -> "Timer Start Event"
    words = [word.capitalize() for word in re.split(r'(?=[A-Z])', capitalize_fc(name)) if word]
    return " ".join(words)


def bounds_to_bb(bounds: Element) -> BoundingBox:
    xywh = {k: to_int_or_float(bounds.get(k)) for k in ["x", "y", "width", "height"]}
    bb = BoundingBox.from_xywh(**xywh, allow_neg_coord=True)
    return bb


def to_int_or_float(s):
    v = float(s)
    return int(v) if v.is_integer() else v


def parse_annotation_background_width(bpmn_path: Path):
    """Get the width the image was resized to when annotating in the BPMN Annotator tool"""
    assert bpmn_path.suffix == ".bpmn", f"{bpmn_path}"
    img_meta_line = bpmn_path.read_text().split("\n")[1]
    assert img_meta_line.startswith(
        "<!--"
    ), f"{bpmn_path} has no meta line, line 1: {img_meta_line}"
    img_meta = json.loads(img_meta_line.replace("<!-- ", "").replace(" -->", ""))
    return img_meta["backgroundSize"]


def split_img_id(img_id: str) -> Tuple[str, str]:
    exercise, writer = img_id.split("_")
    return exercise, writer
