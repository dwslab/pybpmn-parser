import functools
import logging
import math
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple

import numpy as np
import yamlu
from PIL import Image
from lxml import etree
# noinspection PyProtectedMember
from lxml.etree import _Element as Element
from yamlu import img_ops
from yamlu.img import BoundingBox

from pybpmn.util import bounds_to_bb, to_int_or_float, get_omgdi_ns, parse_annotation_background_width

_logger = logging.getLogger(__name__)


def bpmn_to_image(bpmn_path: Path, png_path: Path, shift_to_origin=False):
    """
    :param bpmn_path: path to BPMN XML
    :param png_path: path where the rendered bpmn should be saved to
    :param shift_to_origin: bpmn-to-image aligns diagrams to origin, i.e. it creates an image with diagram shifted
        such that its top-left is close to (0,0), and does not render elements at exact BPMNDI positions.
        when set to False, we undo this operation.
    """
    cmd = ["bpmn-to-image", "--no-title", "--no-footer", f"{bpmn_path}:{png_path}"]
    _logger.debug("Executing: %s", " ".join(cmd))
    subprocess.run(cmd, check=True, capture_output=True)
    img: Image.Image = Image.open(png_path)

    if not shift_to_origin:
        # get bounding box from xml, and revert this shifting operation

        # the bpmn bounding box and the image width/height sometimes do not match due to the BPMNLabels
        # Example: leftmost shape is a start event label.
        # in this case bb.l corresponds to label.l (i.e. BPMNLabel -> omgdc:Bounds -> x attrib in BPMN XML)
        # however, in the generated image the label is typically much smaller due to a small font size
        # this means i can't just place the generated image at the bpmn bounding box left+top offset
        # TODO figure out how to generate image that is not aligned to origin
        bb = _get_approx_bpmn_bounding_box(bpmn_path)

        left_offset = bb.lr_mid - img.width / 2.0
        top_offset = bb.tb_mid - img.height / 2.0

        size = math.ceil(left_offset + img.width), math.ceil(top_offset + img.height)
        img_orig_size = Image.new("RGBA", size, (255, 255, 255, 0))
        img_orig_size.paste(img, box=(int(round(left_offset)), int(round(top_offset))))
        img = img_orig_size

    img.save(png_path)
    # print("rendered bpmn img size:", bpmn_img.size)
    # print("actual bounding box of all bpmn symbols:", bb, "w/h:", bb.w, bb.h)
    return img


class Visualizer:
    def __init__(self, img: Image.Image, color="orange", alpha=1.0):
        self.img = img
        self.color = color
        self.alpha = alpha

    @classmethod
    def from_img_path(cls, img_path: Path, **kwargs):
        img = yamlu.read_img(img_path)
        return cls(img, **kwargs)

    def create_bpmn_overlay_img(self, bpmn_path: Path):
        with tempfile.TemporaryDirectory() as tmpdirname:
            img_bpmn = bpmn_to_image(bpmn_path, png_path=Path(tmpdirname) / f"{bpmn_path.stem}.png")
        img_w = parse_annotation_background_width(bpmn_path)
        return self.create_overlayed_hw_img(img_bpmn, img_w=img_w)

    def create_overlayed_hw_img(self, img_bpmn: Image.Image, img_w=None, interpolation=Image.LANCZOS) -> Image.Image:
        scale = self.img.width / img_w

        # https://stackoverflow.com/questions/13027169/scale-images-with-pil-preserving-transparency-and-color
        target_size = round(img_bpmn.width * scale), round(img_bpmn.height * scale)
        # img_bpmn = img_bpmn.resize(target_size)
        bands = img_bpmn.split()
        bands = [b.resize(target_size, interpolation) for b in bands]
        img_bpmn = Image.merge("RGBA", bands)

        img_overlay = self.img.convert("RGBA").copy()
        # Update: this grayscale transparency with alpha is too thin
        # if self.color == "black":
        #    img_bpmn_transparent = img_ops.grayscale_transparency(img_bpmn)
        #    img_overlay.alpha_composite(img_bpmn_transparent)
        # else:
        img_bpmn_transparent = img_ops.white_to_transparency(img_bpmn, thresh=200)
        img_bpmn_transparent = img_ops.black_to_color(img_bpmn_transparent, self.color)
        if self.alpha < 1.0:
            # noinspection PyTypeChecker
            img_np = np.asarray(img_bpmn_transparent).copy()
            img_np[..., -1] = np.round(img_np[..., -1] * self.alpha).astype(img_np.dtype)
            img_bpmn_transparent = Image.fromarray(img_np)
        img_overlay.paste(img_bpmn_transparent, mask=img_bpmn_transparent)

        return img_overlay


def _get_approx_bpmn_bounding_box(bpmn_path):
    """
    approximated get_bpmn_bounding_box for bpmn_to_image font bounding box issue
    """
    document = etree.parse(str(bpmn_path))
    root = document.getroot()

    diagram = root.find("bpmndi:BPMNDiagram", root.nsmap)
    shape_bounds = diagram.findall(".//bpmndi:BPMNShape/omgdc:Bounds", root.nsmap)
    shape_bbs = [bounds_to_bb(bound) for bound in shape_bounds]

    lbl_bounds = diagram.findall(".//bpmndi:BPMNLabel/omgdc:Bounds", root.nsmap)
    lbl_bbs = [bounds_to_bb(bound) for bound in lbl_bounds]
    for lbl_bb in lbl_bbs:
        # bpmn-js seems to align font vertically to top, and horizontally to center
        # since font is typically much smaller than handwriting, cut lower part of box as a heuristic
        lbl_bb.b = lbl_bb.tb_mid

    waypoints = diagram.findall(f".//{get_omgdi_ns(diagram)}:waypoint", diagram.nsmap)
    pts = np.array([[to_int_or_float(wp.get("x")), to_int_or_float(wp.get("y"))] for wp in waypoints])
    pts_bbs = [BoundingBox.from_points(pts, allow_neg_coord=True)] if len(pts) > 0 else []

    bb = functools.reduce(lambda bb1, bb2: bb1.union(bb2), [*shape_bbs, *lbl_bbs, *pts_bbs])
    return bb


def get_bpmn_bounding_box(bpmn_path):
    """
    :return: the smallest bounding box that covers all diagram symbols
    """
    document = etree.parse(str(bpmn_path))

    bounds, waypoints = get_bpmn_bounds_waypoints(document)

    pts = np.array([[to_int_or_float(wp.get("x")), to_int_or_float(wp.get("y"))] for wp in waypoints])
    pts_bbs = [BoundingBox.from_points(pts, allow_neg_coord=True)] if len(pts) > 0 else []

    bounds_bbs = [bounds_to_bb(bound) for bound in bounds]
    bb = functools.reduce(lambda bb1, bb2: bb1.union(bb2), bounds_bbs + pts_bbs)
    return bb


def get_bpmn_bounds_waypoints(document) -> Tuple[List[Element], List[Element]]:
    root = document.getroot()
    diagram = root.find("bpmndi:BPMNDiagram", root.nsmap)
    bounds = diagram.findall(".//omgdc:Bounds", root.nsmap)

    ns = get_omgdi_ns(diagram)
    waypoints = diagram.findall(f".//{ns}:waypoint", diagram.nsmap)

    return bounds, waypoints
