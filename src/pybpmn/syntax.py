import yamlu

POOL = "pool"
LANE = "lane"
COLLABORATION_CATEGORIES = [POOL, LANE]

ACTIVITY_CATEGORIES = [
    "task",
    "subProcessCollapsed",
    "subProcessExpanded",
    "callActivity",
]
MESSAGE_EVENTS = [
    "messageStartEvent",
    "messageIntermediateCatchEvent",
    "messageIntermediateThrowEvent",
    "messageEndEvent",
]
TIMER_INTERMEDIATE_EVENT = "timerIntermediateEvent"
TIMER_EVENTS = ["timerStartEvent", TIMER_INTERMEDIATE_EVENT]

INTERMEDIATE_EVENT = "intermediateEvent"
EVENT_CATEGORIES = (
        ["startEvent", INTERMEDIATE_EVENT, "endEvent"] + MESSAGE_EVENTS + TIMER_EVENTS
)

GATEWAY_CATEGORIES = [
    "exclusiveGateway",
    "parallelGateway",
    "inclusiveGateway",
    "eventBasedGateway",
]
NODE_CATEGORIES = ACTIVITY_CATEGORIES + GATEWAY_CATEGORIES + EVENT_CATEGORIES

DATA_OBJECT = "dataObject"
DATA_STORE = "dataStore"
BUSINESS_OBJECT_CATEGORIES = [DATA_OBJECT, DATA_STORE]

ANNOTATION_SHAPE_CATEGORIES = ["textAnnotation"]

# bpmndi:BPMNShape
BPMNDI_SHAPE_CATEGORIES = [
    *ACTIVITY_CATEGORIES,
    *EVENT_CATEGORIES,
    *GATEWAY_CATEGORIES,
    *COLLABORATION_CATEGORIES,
    *BUSINESS_OBJECT_CATEGORIES,
    *ANNOTATION_SHAPE_CATEGORIES,
]

# bpmndi:BPMNEdge
# - association is for textAnnotation
# - bpmn dataInputAssociation and dataOutputAssociation are collapsed into a single dataAssociation category
DATA_ASSOCIATION = "dataAssociation"
MESSAGE_FLOW = "messageFlow"
BPMNDI_EDGE_CATEGORIES = ["sequenceFlow", MESSAGE_FLOW, DATA_ASSOCIATION, "association"]

# bpmndi:BPMNLabel
LABEL = "label"
BPMNDI_LABEL_CATEGORIES = [LABEL]

CATEGORY_GROUPS = {
    "activity": ACTIVITY_CATEGORIES,
    "event": EVENT_CATEGORIES,
    "gateway": GATEWAY_CATEGORIES,
    "collaboration": COLLABORATION_CATEGORIES,
    "business_object": BUSINESS_OBJECT_CATEGORIES,
    "annotation": ANNOTATION_SHAPE_CATEGORIES,
    "label": BPMNDI_LABEL_CATEGORIES,
    "edge": BPMNDI_EDGE_CATEGORIES,
}

BPMNDI_SHAPE_GROUPS = [
    "activity",
    "event",
    "gateway",
    "collaboration",
    "business_object",
    "annotation",
]

ALL_CATEGORIES = yamlu.flatten(CATEGORY_GROUPS.values())

EVENT_CATEGORY_TO_NO_POS_TYPE = {
    "startEvent": "event",
    "intermediateEvent": "event",
    "endEvent": "event",
    "messageStartEvent": "messageEvent",
    "messageIntermediateCatchEvent": "messageEvent",
    "messageIntermediateThrowEvent": "messageEvent",
    "messageEndEvent": "messageEvent",
    "timerStartEvent": "timerEvent",
    "timerIntermediateEvent": "timerEvent",
}

CATEGORY_TO_PAPER_NAME = {
    "task": "Task",
    "subProcessCollapsed": "Subprocess (collapsed)",
    "subProcessExpanded": "Subprocess (expanded)",
    "callActivity": "Call Activity",
    "startEvent": "Start Event",
    "intermediateEvent": "Intermediate Event",
    "endEvent": "End Event",
    "messageStartEvent": "Message Start Event",
    "messageIntermediateCatchEvent": "Message Intermediate Catch Event",
    "messageIntermediateThrowEvent": "Message Intermediate Throw Event",
    "messageEndEvent": "Message End Event",
    "timerStartEvent": "Timer Start Event",
    "timerIntermediateEvent": "Timer Intermediate Event",
    "exclusiveGateway": "Exclusive Gateway",
    "parallelGateway": "Parallel Gateway",
    "inclusiveGateway": "Inclusive Gateway",
    "eventBasedGateway": "Event-based Gateway",
    "sequenceFlow": "Sequence Flow",
    "messageFlow": "Message Flow",
    "dataAssociation": "Data Association",
    "association": "Association",
    "pool": "Pool",
    "lane": "Lane",
    "dataObject": "Data Object",
    "dataStore": "Data Store",
    "textAnnotation": "Text Annotation",
    "label": "Label",
    "event": "Event",
    "messageEvent": "Message Event",
    "timerEvent": "Timer Event",
    "subProcess": "Subprocess",
}


def _check_inconsistencies():
    n1 = (
            len(BPMNDI_SHAPE_CATEGORIES)
            + len(BPMNDI_EDGE_CATEGORIES)
            + len(BPMNDI_LABEL_CATEGORIES)
    )
    n2 = sum(len(g) for g in CATEGORY_GROUPS.values())
    assert n1 == n2, f"{n1}, {n2}"


_check_inconsistencies()
