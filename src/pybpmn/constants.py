VALID_SPLITS = ("train", "val", "test")

# --- Relations ---
ARROW_NEXT_REL = "arrow_next"
ARROW_PREV_REL = "arrow_prev"
TEXT_BELONGS_TO_REL = "text_belongs_to"
ARROW_KEYPOINT_FIELDS = ("tail", "head")
ARROW_RELATIONS = (ARROW_PREV_REL, ARROW_NEXT_REL)
RELATIONS = (*ARROW_RELATIONS, TEXT_BELONGS_TO_REL)

# my bpmn namespace mapping
NS_MODEL = 'http://www.omg.org/spec/BPMN/20100524/MODEL'
NS_MAP = {
    None: NS_MODEL,
    'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
    'omgdc': 'http://www.omg.org/spec/DD/20100524/DC',
    'omgdi': 'http://www.omg.org/spec/DD/20100524/DI',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
}
