import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

import numpy as np
import yamlu
from PIL import Image
from lxml import etree
# noinspection PyProtectedMember
from lxml.etree import _Element as Element
from yamlu.img import AnnotatedImage, Annotation, BoundingBox

from pybpmn import syntax
from pybpmn.constants import *
from pybpmn.util import bounds_to_bb, to_int_or_float, parse_annotation_background_width, capitalize_fc

_logger = logging.getLogger(__name__)

BPMN_ATTRIB_TO_RELATION = {"sourceRef": ARROW_PREV_REL, "targetRef": ARROW_NEXT_REL}


def parse_bpmn_anns(bpmn_path: Path):
    return BpmnParser().parse_bpmn_anns(bpmn_path)


class InvalidBpmnException(Exception):
    def __init__(self, error_type: str, details: str = None):
        """
        :param error_type: makes it possible to group errors by type
        :param details: can be used to log file specific error details
        """
        super().__init__(error_type if details is None else f"{error_type}: {details}")
        self.error_type = error_type
        self.details = details


class BpmnParser:
    def __init__(
            self,
            arrow_min_wh: int = 20,
            img_max_size_ref: int = 1000,
            excluded_categories: Set[str] = None,
            excluded_label_categories: Set[str] = None,
            link_text_rel_two_way: bool = False,
            link_pools: bool = True,
            link_lanes: bool = True,
            scale_to_ann_width: bool = True
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
        self.link_pools = link_pools
        self.link_lanes = link_lanes
        self.scale_to_ann_width = scale_to_ann_width

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

        try:
            anns = self.parse_bpmn_anns(bpmn_path)
        except Exception as e:
            _logger.error("Error while parsing: %s", bpmn_path)
            raise e

        img = yamlu.read_img(img_path)

        arrow_min_wh = self.arrow_min_wh
        if self.scale_to_ann_width:
            self.scale_anns_to_img_width_(anns, bpmn_path, img)
            arrow_min_wh = self.arrow_min_wh * max(img.size) / self.img_max_size_ref

        edge_anns = [a for a in anns if a.category in syntax.BPMNDI_EDGE_CATEGORIES]
        self.resize_arrows_to_min_wh(edge_anns, arrow_min_wh)

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

        choreographies = root.findall("choreography", NS_MAP)
        if len(choreographies) > 0:
            # slight abuse of the exception class as this is not per se invalid BPMN
            raise InvalidBpmnException("BPMN Choreography diagrams are not implemented.")

        collaborations = root.findall("collaboration", NS_MAP)
        for collaboration in collaborations:
            id_to_obj.update(_create_id_to_obj_mapping(collaboration))

        for process in root.findall("process", NS_MAP):
            id_to_obj.update(_create_id_to_obj_mapping(process))

        diagram = root.find("bpmndi:BPMNDiagram", NS_MAP)
        plane = diagram[0]
        shapes = plane.findall("bpmndi:BPMNShape", NS_MAP)
        edges = plane.findall("bpmndi:BPMNEdge", NS_MAP)
        elements = shapes + edges

        associations = []
        anns = []
        id_to_ann = {}
        for element in elements:
            model_id = element.get("bpmnElement")
            if model_id not in id_to_obj:
                raise InvalidBpmnException("Missing model element", f"{bpmn_path}: {model_id}")
            model_element = id_to_obj[model_id]
            if get_ns(model_element) != NS_MODEL:
                _logger.warning("%s: skipping %s element with custom namespace", bpmn_path, model_element.tag)
                continue
            category = get_category(element, model_element)

            # only edge type that can have another edge as src or target
            # therefore has to be separated and moved to the end
            if category == syntax.ASSOCIATION:
                associations.append(element)
                continue
            if category in syntax.BPMNDI_SHAPE_CATEGORIES:
                element_anns = _shape_to_anns(element, model_element, has_pools=len(collaborations) > 0)
            else:
                element_anns = _edge_to_anns(element, model_element, id_to_ann)
            anns += element_anns
            for ann in element_anns:
                if ann.category != syntax.LABEL:
                    id_to_ann[ann.id] = ann

        for association in associations:
            model_element = id_to_obj[association.get("bpmnElement")]
            anns += _edge_to_anns(association, model_element, id_to_ann)

        self._link_text_rel_anns(anns)
        if self.link_pools:
            self._link_pools(anns)
        if self.link_lanes:
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
                pool_ann = process_id_to_ann.get(a.get("pool"), None)
                a.set("pool", pool_ann)

    def _link_lanes(self, anns, root):
        # NOTE: This only selects top-level lanes and no nested lanes
        flow_nodes = root.findall("process/laneSet/lane/flowNodeRef", NS_MAP)
        if len(flow_nodes) == 0:
            return

        id_to_ann = {a.id: a for a in anns if a.category != "label"}
        for flow_node in flow_nodes:
            # e.g. <flowNodeRef>Event_00v8k43</flowNodeRef>
            node_ann = id_to_ann.get(flow_node.text, None)
            if node_ann is None:
                raise InvalidBpmnException("Invalid Lane flowNodeRef id", flow_node.text)
            lane_ann = id_to_ann[flow_node.getparent().get("id")]
            node_ann.lane = lane_ann

    def scale_anns_to_img_width_(self, anns: List[Annotation], bpmn_path: Path, img: Image.Image):
        img_w_annotation = parse_annotation_background_width(bpmn_path)
        scale = img.width / img_w_annotation

        for a in anns:
            a.bb = a.bb.scale(scale)

            if not a.bb.is_within_img(img.width, img.height):
                _logger.debug(
                    "%s: clipping bb %s to img (%d,%d)",
                    bpmn_path.name,
                    a.bb,
                    img.width,
                    img.height,
                )
                a.bb = a.bb.clip_to_image(img.width, img.height)
        for a in anns:
            if "waypoints" in a:
                a.waypoints = a.waypoints * scale

                a.tail = a.waypoints[0]
                a.head = a.waypoints[-1]

    def resize_arrows_to_min_wh(self, edge_anns: List[Annotation], arrow_min_wh: float):
        for a in edge_anns:
            assert a.category in syntax.BPMNDI_EDGE_CATEGORIES

            a.bb = a.bb.pad_min_size(
                w_min=arrow_min_wh, h_min=arrow_min_wh
            )


def get_ns(element: Element):
    tag_str = element.tag
    i = tag_str.find("}")
    if i == -1:
        return element.nsmap[None]
    return tag_str[1:i]


def get_tag_without_ns(element: Element):
    tag_str = element.tag
    return tag_str[tag_str.find("}") + 1:]


def get_category(bpmndi_element: Element, model_element: Element):
    """inverse operation of get_tag"""

    # remove namespace from tag
    category: str = get_tag_without_ns(model_element)

    # startEvent, endEvent, intermediateCatchEvent, intermediateThrowEvent, boundaryEvent
    if category.endswith("Event"):
        # types are definition childrens: terminateEventDefinition, messageEventDefinition, timerEventDefinition
        # NOTE parallelMultipleEvent has multiple definitions e.g. timer + message
        event_types = [t for t in syntax.EVENT_DEFINITIONS if
                       model_element.find(f"{t}EventDefinition", NS_MAP) is not None]
        if len(event_types) == 1:
            # startEvent -> messageStartEvent, endEvent -> terminateEndEvent, boundaryEvent -> timerBoundaryEvent...
            category = event_types[0] + capitalize_fc(category)
        elif len(event_types) > 1:
            # parallel multiple are always catch events, so this is an error in the BPMN XML file
            # same for boundaryEvents which should only have one event type
            if category in {"intermediateThrowEvent", syntax.END_EVENT, "boundaryEvent"}:
                raise InvalidBpmnException(f"Invalid {category} with multiple event definitions", ",".join(event_types))
            category = syntax.PARALLEL_MULTIPLE_PREFIX + capitalize_fc(category)

    category_mappings = {
        # events
        "intermediateThrowEvent": syntax.INTERMEDIATE_EVENT,
        "timerIntermediateCatchEvent": syntax.TIMER_INTERMEDIATE_EVENT,
        # collaboration
        "participant": syntax.POOL,
        # data association
        "dataInputAssociation": syntax.DATA_ASSOCIATION,
        "dataOutputAssociation": syntax.DATA_ASSOCIATION,
        # data elements (remove 'Reference' suffix)
        "dataObjectReference": syntax.DATA_OBJECT,
        "dataStoreReference": syntax.DATA_STORE,
    }
    category = category_mappings.get(category, category)

    if category == "subProcess":
        # <bpmndi:BPMNShape id="Activity_1cnm0ru_di" bpmnElement="Activity_1cnm0ru" isExpanded="true">
        #         <omgdc:Bounds x="473" y="455" width="452" height="190" />
        #       </bpmndi:BPMNShape>
        is_expanded = bpmndi_element.get("isExpanded", "false").lower() == "true"
        category = syntax.SUBPROCESS_EXPANDED if is_expanded else syntax.SUBPROCESS_COLLAPSED

    # if category not in syntax.ALL_CATEGORIES:
    #    _logger.warning(f"Unknown category: {category}")
    msg = f"{get_tag_without_ns(model_element)} {model_element.attrib} unknown category: {category}"
    assert category in syntax.ALL_CATEGORIES, msg

    return category


def _create_id_to_obj_mapping(element):
    id_to_obj = {}
    to_visit = [element]
    while len(to_visit) != 0:
        element = to_visit.pop()
        for child in element:
            if get_ns(child) != NS_MODEL:
                continue

            to_visit.append(child)  # BFS

            eid = child.get("id")
            if eid is None:
                continue
            if eid not in id_to_obj:
                id_to_obj[eid] = child
                continue

            # special case (which normally should not happen): there is another model element with the same id
            existing_element = id_to_obj[eid]
            existing_tag = get_tag_without_ns(existing_element)
            child_tag = get_tag_without_ns(child)
            # ignore multiInstanceLoopCharacteristics etc.
            if child.getparent() == existing_element and child_tag in {"multiInstanceLoopCharacteristics",
                                                                       "standardLoopCharacteristics"}:
                # do not overwrite existing mapping
                continue
            if existing_tag == child_tag and child_tag in {"dataObjectReference", "dataStoreReference", "dataState"}:
                # sometimes data elements are listed multiple times
                continue
            raise InvalidBpmnException("Duplicate model element id", f"{eid} (existing={existing_tag}, new={child_tag}")

    return id_to_obj


def _edge_to_anns(edge: Element, model_element: Element, id_to_ann: Dict[str, Annotation]):
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

    waypoints = np.array(
        [[to_int_or_float(wp.get("x")), to_int_or_float(wp.get("y"))] for wp in
         edge.findall("omgdi:waypoint", NS_MAP)]
    )
    if len(waypoints) == 0:
        raise InvalidBpmnException(f"{category} without waypoints")
    bb = BoundingBox.from_points(waypoints, allow_neg_coord=True)

    attrib = _parse_edge_attribs(model_element)
    # create Annotation links instead of linking through id
    for rel in ARROW_RELATIONS:
        if rel not in attrib:
            continue
        sid = attrib[rel]
        ann = id_to_ann.get(sid, None)
        if ann is None and category == syntax.ASSOCIATION:
            # TODO implement that associations can be connected to other associations
            raise InvalidBpmnException("Association has another association as src or target", sid)
        attrib[rel] = ann
    anns = [Annotation(category, bb, waypoints=waypoints, **attrib)]

    lbl_ann = _create_label_ann_if_exists(edge, model_element)
    if lbl_ann is not None:
        anns.append(lbl_ann)

    return anns


def _shape_to_anns(shape: Element, model_element: Element, has_pools: bool) -> List[Annotation]:
    category = get_category(shape, model_element)

    bounds = shape.find("omgdc:Bounds", NS_MAP)

    shape_ann = Annotation(
        category=category,
        bb=bounds_to_bb(bounds),
        **model_element.attrib
    )
    if has_pools and category != syntax.POOL:
        # shapes are children of process, except for lanes, which are separated by one or more additional laneSets
        parent = model_element.getparent()
        #   <process id="Process_1gpwvpe">
        #     <laneSet id="LaneSet_0gwy363">
        #       <lane id="Lane_0mgb3fg" name="Claim officer">
        if category == syntax.LANE:
            parent = parent.getparent()
        if get_tag_without_ns(parent) == "process":
            shape_ann.pool = parent.get("id")

    if get_tag_without_ns(model_element) == "textAnnotation":
        text_el = model_element.find("text", NS_MAP)
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
            if old not in attrib:
                raise InvalidBpmnException(f"{tag} has no {old} attrib", str(attrib))
            attrib[new] = attrib.pop(old)
    elif tag == "dataInputAssociation":
        # overwrite Property targetRef
        # TODO what is this property for?
        attrib[ARROW_PREV_REL] = model_element.find("sourceRef", NS_MAP).text
        attrib[ARROW_NEXT_REL] = model_element.getparent().get("id")
    elif tag == "dataOutputAssociation":
        attrib[ARROW_PREV_REL] = model_element.getparent().get("id")
        attrib[ARROW_NEXT_REL] = model_element.find("targetRef", NS_MAP).text
    else:
        raise ValueError(f"Unknown edge tag: {tag}")

    return attrib


def _create_label_ann_if_exists(shape_or_edge, model_element) -> Optional[Annotation]:
    label = shape_or_edge.find("bpmndi:BPMNLabel", NS_MAP)
    if label is None:
        return None

    text = model_element.get("name")
    if text is None or text.strip() == "":
        return None

    # BPMN Spec. p. 382: "The bounds of the BPMNLabel are optional"
    bounds = label.find("omgdc:Bounds", NS_MAP)
    if bounds is None:
        return None

    a = Annotation(category="label", bb=bounds_to_bb(bounds), name=text)
    a.set(TEXT_BELONGS_TO_REL, model_element.get("id"))
    return a
