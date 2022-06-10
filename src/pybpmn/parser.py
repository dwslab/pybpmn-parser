import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

import numpy as np
import yamlu
from lxml import etree
# noinspection PyProtectedMember
from lxml.etree import _Element as Element
from yamlu.img import AnnotatedImage, Annotation, BoundingBox

from pybpmn import syntax
from pybpmn.constants import (
    ARROW_NEXT_REL,
    ARROW_PREV_REL,
    ARROW_RELATIONS,
    TEXT_BELONGS_TO_REL,
)
from pybpmn.syntax import EVENT_DEFINITIONS
from pybpmn.util import bounds_to_bb, to_int_or_float, get_omgdi_ns, parse_annotation_background_width

_logger = logging.getLogger(__name__)

BPMN_ATTRIB_TO_RELATION = {"sourceRef": ARROW_PREV_REL, "targetRef": ARROW_NEXT_REL}


def parse_bpmn_anns(bpmn_path: Path):
    return BpmnParser().parse_bpmn_anns(bpmn_path)


class BpmnParser:
    def __init__(
            self,
            arrow_min_wh: int = 20,
            img_max_size_ref: int = 1000,
            excluded_categories: Set[str] = None,
            excluded_label_categories: Set[str] = None,
            link_text_rel_two_way: bool = False,
    ):
        """
        :param arrow_min_wh: pad edge bounding boxes so that their w and h is at least arrow_min_wh
                             when the image is scaled to img_max_size_ref
        :param img_max_size_ref: reference image size to consider for arrow_min_wh
        :param excluded_label_categories: categories for which label annotations should not be parsed
        """
        self.arrow_min_wh = arrow_min_wh
        self.img_max_size_ref = img_max_size_ref
        self.excluded_categories = {} if excluded_categories is None else excluded_categories
        self.excluded_label_categories = {} if excluded_label_categories is None else excluded_label_categories
        self.link_text_rel_two_way = link_text_rel_two_way

    def _is_included_ann(self, a: Annotation) -> bool:
        if a.category in self.excluded_categories:
            return False
        if a.category == "label" and a.get(TEXT_BELONGS_TO_REL).category in self.excluded_label_categories:
            return False
        return True

    # noinspection PyPropertyAccess
    def parse_bpmn_img(self, bpmn_path: Path, img_path: Path) -> AnnotatedImage:
        """
        :param bpmn_path: path to the BPMN XML file
        :param img_path: path to the corresponding BPMN image
        """
        img = yamlu.read_img(img_path)
        img_w, img_h = img.size

        img_w_annotation = parse_annotation_background_width(bpmn_path)
        scale = img_w / img_w_annotation
        arrow_min_wh_scaled = self.arrow_min_wh * max(img.size) / self.img_max_size_ref

        try:
            anns = self.parse_bpmn_anns(bpmn_path)
            for a in anns:
                a.bb = a.bb.scale(scale)

                if a.category in syntax.BPMNDI_EDGE_CATEGORIES:
                    a.bb = a.bb.pad_min_size(
                        w_min=arrow_min_wh_scaled, h_min=arrow_min_wh_scaled
                    )

                if not a.bb.is_within_img(img_w, img_h):
                    _logger.debug(
                        "%s: clipping bb %s to img (%d,%d)",
                        bpmn_path.name,
                        a.bb,
                        img_w,
                        img_h,
                    )
                    a.bb = a.bb.clip_to_image(img_w, img_h)
            for a in anns:
                if "waypoints" in a:
                    a.waypoints = a.waypoints * scale

                    a.tail = a.waypoints[0]
                    a.head = a.waypoints[-1]
        except Exception as e:
            _logger.error("Error while processing: %s", bpmn_path)
            raise e

        anns = [a for a in anns if self._is_included_ann(a)]

        return AnnotatedImage(
            img_path.name,
            width=img.width,
            height=img.height,
            annotations=anns,
            img=img,
        )

    def parse_bpmn_anns(self, bpmn_path: Path) -> List[Annotation]:
        document = etree.parse(str(bpmn_path))
        root = document.getroot()

        id_to_obj = {}

        collaborations = root.findall("collaboration", root.nsmap)
        for collaboration in collaborations:
            id_to_obj.update(_create_id_to_obj_mapping(collaboration))

        for process in root.findall("process", root.nsmap):
            id_to_obj.update(_create_id_to_obj_mapping(process))

        diagram = root.find("bpmndi:BPMNDiagram", root.nsmap)
        plane = diagram[0]
        shapes = plane.findall("bpmndi:BPMNShape", plane.nsmap)
        shape_anns = yamlu.flatten(
            _shape_to_anns(shape, id_to_obj[shape.get("bpmnElement")], has_pools=len(collaborations) > 0)
            for shape in shapes
        )
        id_to_shape_ann = {a.id: a for a in shape_anns if a.category != "label"}

        edges = plane.findall("bpmndi:BPMNEdge", plane.nsmap)

        edge_anns = []
        for edge in edges:
            model_id = edge.get("bpmnElement")
            if model_id not in id_to_obj:
                raise ValueError(f"{bpmn_path}: {model_id} not in model element ids")
            edge_anns.append(_edge_to_anns(edge, id_to_obj[model_id], id_to_shape_ann))

        edge_anns = yamlu.flatten(edge_anns)

        anns = shape_anns + edge_anns
        self._link_text_rel_anns(anns)
        self._link_pools(anns)
        self._link_lanes(anns, root)
        return anns

    def _link_text_rel_anns(self, anns):
        id_to_ann = {a.id: a for a in anns if a.category != "label"}

        lbl_anns = [a for a in anns if a.category == "label"]

        for lbl_ann in lbl_anns:
            symb_ann = id_to_ann[lbl_ann.get(TEXT_BELONGS_TO_REL)]
            lbl_ann.set(TEXT_BELONGS_TO_REL, symb_ann)
            if self.link_text_rel_two_way:
                symb_ann.set(TEXT_BELONGS_TO_REL, lbl_ann)

    def _link_pools(self, anns):
        # collapsed pools do not have a "processRef" and can be omitted
        process_id_to_ann = {a.processRef: a for a in anns if a.category == syntax.POOL and "processRef" in a}
        for a in anns:
            if "pool" in a:
                pool_ann = process_id_to_ann[a.get("pool")]
                a.set("pool", pool_ann)

    def _link_lanes(self, anns, root):
        # NOTE: This only selects top-level lanes and no nested lanes
        flow_nodes = root.findall("process/laneSet/lane/flowNodeRef", root.nsmap)
        if len(flow_nodes) == 0:
            return

        id_to_ann = {a.id: a for a in anns if a.category != "label"}
        for flow_node in flow_nodes:
            # e.g. <flowNodeRef>Event_00v8k43</flowNodeRef>
            node_ann = id_to_ann[flow_node.text]
            lane_ann = id_to_ann[flow_node.getparent().get("id")]
            node_ann.lane = lane_ann


def get_tag_without_ns(element: Element):
    tag_str = element.tag
    return tag_str[tag_str.find("}") + 1:]


def get_category(bpmndi_element: Element, model_element: Element):
    """inverse operation of get_tag"""

    # remove namespace from tag
    category: str = get_tag_without_ns(model_element)

    # startEvent, endEvent, intermediateCatchEvent, intermediateThrowEvent
    if category.endswith("Event"):
        for event_type in EVENT_DEFINITIONS:
            # types are definition childrens: terminateEventDefinition, messageEventDefinition, timerEventDefinition
            if model_element.find(f"{event_type}EventDefinition", model_element.nsmap) is not None:
                # startEvent -> messageStartEvent, endEvent -> terminateEndEvent, ...
                category = f"{event_type}{category[0].upper()}{category[1:]}"
    # further shortening of untyped  and terminate events
    if category == "intermediateThrowEvent":
        category = syntax.INTERMEDIATE_EVENT
    elif category == "timerIntermediateCatchEvent":
        category = syntax.TIMER_INTERMEDIATE_EVENT
    elif category == "participant":
        category = syntax.POOL
    elif category == "subProcess":
        # <bpmndi:BPMNShape id="Activity_1cnm0ru_di" bpmnElement="Activity_1cnm0ru" isExpanded="true">
        #         <omgdc:Bounds x="473" y="455" width="452" height="190" />
        #       </bpmndi:BPMNShape>
        is_expanded = bpmndi_element.get("isExpanded", "false").lower() == "true"
        category = "subProcessExpanded" if is_expanded else "subProcessCollapsed"
    elif category in ["dataInputAssociation", "dataOutputAssociation"]:
        category = syntax.DATA_ASSOCIATION
    elif category in ["dataObjectReference", "dataStoreReference"]:
        # remove 'Reference' suffix
        category = category[: -len("Reference")]

    assert category in syntax.ALL_CATEGORIES, f"unknown category: {category}"

    return category


def _create_id_to_obj_mapping(element):
    id_to_obj = {}
    to_visit = [element]
    while len(to_visit) != 0:
        element = to_visit.pop()
        for child in element:
            to_visit.append(child)
            if child.get("id") is not None:
                id_to_obj[child.get("id")] = child
    return id_to_obj


def _edge_to_anns(edge: Element, model_element: Element, id_to_shape_ann: Dict[str, Annotation]):
    """
    Parses edges (see syntax.BPMNDI_EDGE_CATEGORIES)
    :param edge the BPMNDI edge element
    :param model_element the corresponding model element
    (this is relevant for arrows where the waypoints don't include the width/height of the arrow head)

    Example edge:
     <bpmndi:BPMNEdge id="Flow_0n46wz3_di" bpmnElement="Flow_0n46wz3">
           <omgdi:waypoint x="380" y="120" />
           <omgdi:waypoint x="391" y="120" />
           <omgdi:waypoint x="391" y="124" />
           <omgdi:waypoint x="402" y="124" />
     </bpmndi:BPMNEdge>
     Examples model_element: see parse_edge_attribs()
    """
    category = get_category(edge, model_element)

    ns = get_omgdi_ns(edge)
    waypoints = np.array(
        [[to_int_or_float(wp.get("x")), to_int_or_float(wp.get("y"))] for wp in
         edge.findall(f"{ns}:waypoint", edge.nsmap)]
    )
    bb = BoundingBox.from_points(waypoints, allow_neg_coord=True)

    attrib = _parse_edge_attribs(model_element)
    # create Annotation links instead of linking through id
    for rel in ARROW_RELATIONS:
        attrib[rel] = id_to_shape_ann[attrib[rel]]
    anns = [Annotation(category, bb, waypoints=waypoints, **attrib)]

    lbl_ann = _create_label_ann_if_exists(edge, model_element)
    if lbl_ann is not None:
        anns.append(lbl_ann)

    return anns


def _shape_to_anns(shape: Element, model_element: Element, has_pools: bool) -> List[Annotation]:
    category = get_category(shape, model_element)

    shape_ann = Annotation(
        category=category,
        bb=_child_bounds_to_bb(shape),
        **model_element.attrib
    )
    if has_pools and category not in syntax.COLLABORATION_CATEGORIES:
        parent = model_element.getparent()
        if get_tag_without_ns(parent) == "process":
            shape_ann.pool = parent.get("id")

    if get_tag_without_ns(model_element) == "textAnnotation":
        text_el = model_element.find("text", model_element.nsmap)
        if text_el is not None:
            shape_ann.name = text_el.text

    anns = [shape_ann]
    lbl_ann = _create_label_ann_if_exists(shape, model_element)
    if lbl_ann is not None:
        anns.append(lbl_ann)

    return anns


def _parse_edge_attribs(model_element):
    """
    There are five edge types.
    Examples for 3:
    <sequenceFlow id="Flow_05uk4nb" sourceRef="Gateway_0kzfuhq" targetRef="Activity_0wh26g5" />
    <messageFlow id="Flow_0ibqf49" name="claim with relevant documentation"
                 sourceRef="Participant_1bpc1tq" targetRef="Event_1rrmjoa" />
    <association id="Association_1hh3hfo" sourceRef="Activity_0ok2tf7" targetRef="TextAnnotation_1wf4qj4" />

    The only thing that's a bit more tricky is dataInputAssociation/dataOutputAssociation:
    <task id="Activity_0cjvk33">
          <incoming>Flow_1yvdi3d</incoming>
          <outgoing>Flow_03w517o</outgoing>
          <property id="Property_0e2q2qb" name="__targetRef_placeholder" />
          <dataInputAssociation id="DataInputAssociation_1oljks3">
            <sourceRef>DataObjectReference_1npgwnw</sourceRef>
            <targetRef>Property_0e2q2qb</targetRef>
          </dataInputAssociation>
          <dataOutputAssociation id="DataOutputAssociation_15su1d2">
            <targetRef>DataObjectReference_1525ioa</targetRef>
          </dataOutputAssociation>
        </task>
    """
    attrib = dict(model_element.attrib)
    tag = get_tag_without_ns(model_element)

    if tag in ["sequenceFlow", "messageFlow", "association"]:
        for old, new in BPMN_ATTRIB_TO_RELATION.items():
            attrib[new] = attrib.pop(old)
    elif tag == "dataInputAssociation":
        # overwrite Property targetRef
        # TODO what is this property for?
        attrib[ARROW_PREV_REL] = model_element.find("sourceRef", model_element.nsmap).text
        attrib[ARROW_NEXT_REL] = model_element.getparent().get("id")
    elif tag == "dataOutputAssociation":
        attrib[ARROW_PREV_REL] = model_element.getparent().get("id")
        attrib[ARROW_NEXT_REL] = model_element.find("targetRef", model_element.nsmap).text
    else:
        raise ValueError(f"Unknown edge tag: {tag}")

    return attrib


def _create_label_ann_if_exists(shape_or_edge, model_element) -> Optional[Annotation]:
    label = shape_or_edge.find("bpmndi:BPMNLabel", shape_or_edge.nsmap)
    if label is None:
        return None

    text = model_element.get("name")
    if text is None or text.strip() == "":
        return None

    a = Annotation(category="label", bb=_child_bounds_to_bb(label), name=text)
    a.set(TEXT_BELONGS_TO_REL, model_element.get("id"))
    return a


def _child_bounds_to_bb(element: Element) -> BoundingBox:
    bounds = element.find("omgdc:Bounds", element.nsmap)
    return bounds_to_bb(bounds)
