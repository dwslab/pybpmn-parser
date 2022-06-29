import yamlu

POOL = "pool"
LANE = "lane"
COLLABORATION_CATEGORIES = [POOL, LANE]

TASK = "task"
SUBPROCESS_COLLAPSED = "subProcessCollapsed"
SUBPROCESS_EXPANDED = "subProcessExpanded"
CALL_ACTIVITY = "callActivity"
ACTIVITY_CATEGORIES = [TASK, SUBPROCESS_COLLAPSED, SUBPROCESS_EXPANDED, CALL_ACTIVITY]

MESSAGE_EVENTS = [
    "messageStartEvent",
    "messageIntermediateCatchEvent",
    "messageIntermediateThrowEvent",
    "messageEndEvent",
]
TIMER_START_EVENT = "timerStartEvent"
TIMER_INTERMEDIATE_EVENT = "timerIntermediateEvent"
TIMER_EVENTS = [TIMER_START_EVENT, TIMER_INTERMEDIATE_EVENT]

START_EVENT = "startEvent"
INTERMEDIATE_EVENT = "intermediateEvent"
END_EVENT = "endEvent"
UNTYPED_EVENTS = [START_EVENT, INTERMEDIATE_EVENT, END_EVENT]
TERMINATE_EVENT = "terminateEndEvent"
EVENT_CATEGORIES = (
        UNTYPED_EVENTS + [TERMINATE_EVENT] + MESSAGE_EVENTS + TIMER_EVENTS
)
# Event definitions are modeled as child elements in BPMN XML:
# terminateEventDefinition, messageEventDefinition, timerEventDefinition
EVENT_DEFINITIONS = ["message", "timer", "terminate"]

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
SEQUENCE_FLOW = "sequenceFlow"
ASSOCIATION = "association"
BPMNDI_EDGE_CATEGORIES = [SEQUENCE_FLOW, MESSAGE_FLOW, DATA_ASSOCIATION, ASSOCIATION]

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
    **{k: "event" for k in UNTYPED_EVENTS},
    **{k: "messageEvent" for k in MESSAGE_EVENTS},
    **{k: "timerEvent" for k in TIMER_EVENTS},
}

CATEGORY_TO_LONG_NAME = {
    TASK: "Task",
    SUBPROCESS_COLLAPSED: "Subprocess (collapsed)",
    SUBPROCESS_EXPANDED: "Subprocess (expanded)",
    CALL_ACTIVITY: "Call Activity",
    START_EVENT: "Start Event",
    INTERMEDIATE_EVENT: "Intermediate Event",
    END_EVENT: "End Event",
    "messageStartEvent": "Message Start Event",
    "messageIntermediateCatchEvent": "Message Intermediate Catch Event",
    "messageIntermediateThrowEvent": "Message Intermediate Throw Event",
    "messageEndEvent": "Message End Event",
    TIMER_START_EVENT: "Timer Start Event",
    TIMER_INTERMEDIATE_EVENT: "Timer Intermediate Event",
    "exclusiveGateway": "Exclusive Gateway",
    "parallelGateway": "Parallel Gateway",
    "inclusiveGateway": "Inclusive Gateway",
    "eventBasedGateway": "Event-based Gateway",
    SEQUENCE_FLOW: "Sequence Flow",
    MESSAGE_FLOW: "Message Flow",
    DATA_ASSOCIATION: "Data Association",
    ASSOCIATION: "Association",
    POOL: "Pool",
    LANE: "Lane",
    DATA_OBJECT: "Data Object",
    DATA_STORE: "Data Store",
    "textAnnotation": "Text Annotation",
    "label": "Label",
    "event": "Event",
    "messageEvent": "Message Event",
    "timerEvent": "Timer Event",
    TERMINATE_EVENT: "Terminate End Event",
    "subProcess": "Subprocess",
}


def _check_inconsistencies():
    n_bpmndi = (
            len(BPMNDI_SHAPE_CATEGORIES)
            + len(BPMNDI_EDGE_CATEGORIES)
            + len(BPMNDI_LABEL_CATEGORIES)
    )
    n_cats = sum(len(g) for g in CATEGORY_GROUPS.values())
    assert n_bpmndi == n_cats, f"{n_bpmndi}, {n_cats}"

    long_cat_names = set(CATEGORY_TO_LONG_NAME.keys())
    all_cats = set(yamlu.flatten(CATEGORY_GROUPS.values()))
    diff = all_cats.difference(long_cat_names)
    assert len(diff) == 0, diff


_check_inconsistencies()
