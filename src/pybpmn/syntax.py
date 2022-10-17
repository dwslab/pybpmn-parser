from pybpmn.util import split_camel_case, capitalize_fc

POOL = "pool"
LANE = "lane"
COLLABORATION_CATEGORIES = [POOL, LANE]

TASK_TYPES = ["send", "receive", "user", "manual", "businessRule", "service", "script"]

TASK = "task"
SUBPROCESS_COLLAPSED = "subProcessCollapsed"
SUBPROCESS_EXPANDED = "subProcessExpanded"
CALL_ACTIVITY = "callActivity"
AD_HOC_SUBPROCESS = "adHocSubProcess"
TASK_TYPE_CATEGORIES = [t + TASK.capitalize() for t in TASK_TYPES]
TRANSACTION = "transaction"
ACTIVITY_CATEGORIES = [
    TASK, SUBPROCESS_COLLAPSED, SUBPROCESS_EXPANDED, CALL_ACTIVITY, AD_HOC_SUBPROCESS, TRANSACTION,
    *TASK_TYPE_CATEGORIES
]
ACTIVITIES_WITH_CHILD_SHAPES = [SUBPROCESS_EXPANDED, AD_HOC_SUBPROCESS, TRANSACTION]

START_EVENT = "startEvent"
INTERMEDIATE_EVENT = "intermediateEvent"
END_EVENT = "endEvent"
UNTYPED_EVENTS = [START_EVENT, INTERMEDIATE_EVENT, END_EVENT]

_im_catch_evt = "intermediateCatchEvent"
_im_throw_evt = "intermediateThrowEvent"
MESSAGE_EVENTS = ["message" + capitalize_fc(t) for t in [START_EVENT, _im_catch_evt, _im_throw_evt, END_EVENT]]
TIMER_START_EVENT = "timerStartEvent"
TIMER_INTERMEDIATE_EVENT = "timerIntermediateEvent"
TIMER_EVENTS = [TIMER_START_EVENT, TIMER_INTERMEDIATE_EVENT]

ESCALATION_EVENTS = ["escalation" + capitalize_fc(t) for t in [START_EVENT, _im_catch_evt, _im_throw_evt, END_EVENT]]
CONDITIONAL_EVENTS = ["conditional" + capitalize_fc(t) for t in [START_EVENT, _im_catch_evt]]
ERROR_EVENTS = ["error" + capitalize_fc(t) for t in [START_EVENT, _im_catch_evt, END_EVENT]]
SIGNAL_EVENTS = ["signal" + capitalize_fc(t) for t in [START_EVENT, _im_catch_evt, _im_throw_evt, END_EVENT]]
MULTIPLE_EVENTS = ["multiple" + capitalize_fc(t) for t in [START_EVENT, _im_catch_evt, _im_throw_evt, END_EVENT]]
PARALLEL_MULTIPLE_PREFIX = "parallelMultiple"
PARALLEL_MULTIPLE_EVENTS = [PARALLEL_MULTIPLE_PREFIX + capitalize_fc(t) for t in [START_EVENT, _im_catch_evt]]
LINK_EVENTS = ["link" + capitalize_fc(t) for t in [_im_catch_evt, _im_throw_evt]]
CANCEL_EVENTS = ["cancel" + capitalize_fc(t) for t in [_im_catch_evt, END_EVENT]]
COMPENSATION_EVENTS = ["compensate" + capitalize_fc(t) for t in
                       [START_EVENT, _im_catch_evt, _im_throw_evt, END_EVENT]]

TERMINATE_EVENT = "terminateEndEvent"

# Event definitions are modeled as child elements in BPMN XML:
# terminateEventDefinition, messageEventDefinition, timerEventDefinition
BOUNDARY_EVENT_TYPES = ["message", "timer", "conditional", "signal", "escalation", "error", "compensate", "cancel"]
BOUNDARY_EVENTS = [d + "BoundaryEvent" for d in BOUNDARY_EVENT_TYPES]
EVENT_DEFINITIONS = BOUNDARY_EVENT_TYPES + ["link", "terminate"]
EVENT_CATEGORIES = (
        UNTYPED_EVENTS + [TERMINATE_EVENT] + MESSAGE_EVENTS + TIMER_EVENTS +
        ESCALATION_EVENTS + CONDITIONAL_EVENTS + ERROR_EVENTS + SIGNAL_EVENTS + MULTIPLE_EVENTS +
        PARALLEL_MULTIPLE_EVENTS + LINK_EVENTS + CANCEL_EVENTS + COMPENSATION_EVENTS +
        BOUNDARY_EVENTS
)

EXCLUSIVE_GATEWAY = "exclusiveGateway"
PARALLEL_GATEWAY = "parallelGateway"
INCLUSIVE_GATEWAY = "inclusiveGateway"
EVENT_BASED_GATEWAY = "eventBasedGateway"
COMPLEX_GATEWAY = "complexGateway"
GATEWAY_CATEGORIES = [
    EXCLUSIVE_GATEWAY,
    PARALLEL_GATEWAY,
    INCLUSIVE_GATEWAY,
    EVENT_BASED_GATEWAY,
    COMPLEX_GATEWAY,
]
NODE_CATEGORIES = ACTIVITY_CATEGORIES + GATEWAY_CATEGORIES + EVENT_CATEGORIES

DATA_OBJECT = "dataObject"
DATA_STORE = "dataStore"
DATA_INPUT = "dataInput"
DATA_OUTPUT = "dataOutput"
BUSINESS_OBJECT_CATEGORIES = [DATA_OBJECT, DATA_STORE, DATA_INPUT, DATA_OUTPUT]

TEXT_ANNOTATION = "textAnnotation"
ANNOTATION_SHAPE_CATEGORIES = [TEXT_ANNOTATION, "group"]

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

SHAPE_CATEGORY_GROUPS = {
    "activity": ACTIVITY_CATEGORIES,
    "event": EVENT_CATEGORIES,
    "gateway": GATEWAY_CATEGORIES,
    "collaboration": COLLABORATION_CATEGORIES,
    "business_object": BUSINESS_OBJECT_CATEGORIES,
    "annotation": ANNOTATION_SHAPE_CATEGORIES,
}

CATEGORY_GROUPS = {
    **SHAPE_CATEGORY_GROUPS,
    "label": BPMNDI_LABEL_CATEGORIES,
    "edge": BPMNDI_EDGE_CATEGORIES,
}

ALL_CATEGORIES = [cat for cats in CATEGORY_GROUPS.values() for cat in cats]

EVENT_CATEGORY_TO_NO_POS_TYPE = {
    **{k: "event" for k in UNTYPED_EVENTS},
    **{k: "messageEvent" for k in MESSAGE_EVENTS},
    **{k: "timerEvent" for k in TIMER_EVENTS},
}

CATEGORY_TO_LONG_NAME = {
    cat: split_camel_case(cat) for cat in [*ALL_CATEGORIES, *set(EVENT_CATEGORY_TO_NO_POS_TYPE.values())]
}
CATEGORY_TO_LONG_NAME.update({
    SUBPROCESS_COLLAPSED: "Subprocess (collapsed)",
    SUBPROCESS_EXPANDED: "Subprocess (expanded)",
    EVENT_BASED_GATEWAY: "Event-based Gateway",
    TERMINATE_EVENT: "Terminate End Event",
    "label": "Label",
    "subProcess": "Subprocess",
})


def _check_inconsistencies():
    n_bpmndi = (
            len(BPMNDI_SHAPE_CATEGORIES)
            + len(BPMNDI_EDGE_CATEGORIES)
            + len(BPMNDI_LABEL_CATEGORIES)
    )
    n_cats = sum(len(g) for g in CATEGORY_GROUPS.values())
    assert n_bpmndi == n_cats, f"{n_bpmndi}, {n_cats}"

    long_cat_names = set(CATEGORY_TO_LONG_NAME.keys())
    all_cats = set(ALL_CATEGORIES)
    diff = all_cats.difference(long_cat_names)
    assert len(diff) == 0, diff


_check_inconsistencies()
