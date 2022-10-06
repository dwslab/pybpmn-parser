from pathlib import Path

from yamlu.img import Annotation

from pybpmn.parser import BpmnParser
from pybpmn import syntax

resource_path = Path(__file__).resolve().parent / "resources"


def test_parse_bpmn():
    bpmn_path = resource_path / "process.bpmn"
    img_path = resource_path / "process.jpg"

    parser = BpmnParser()
    ai = parser.parse_bpmn_img(bpmn_path, img_path)
    assert len(ai.annotations) > 0
    assert ai.filename == img_path.name


def test_bpmn_label_without_bounds():
    bpmn_path = resource_path / "label_without_bounds.bpmn"
    parser = BpmnParser()
    anns = parser.parse_bpmn_anns(bpmn_path)
    assert len(anns) > 0


def test_bpmn_different_ns_mapping():
    bpmn_path = resource_path / "no_default_bpmn_ns.bpmn"
    parser = BpmnParser()
    anns = parser.parse_bpmn_anns(bpmn_path)
    assert len(anns) > 0

def test_bpmn_association_to_sequenceflow():
    bpmn_path = resource_path / "assocation_to_sequence_flow.bpmn"
    parser = BpmnParser()
    anns = parser.parse_bpmn_anns(bpmn_path)
    a = [a for a in anns if a.category == syntax.ASSOCIATION][0]
    assert isinstance(a.arrow_next, Annotation)
    assert a.arrow_next.category == syntax.TEXT_ANNOTATION
    assert isinstance(a.arrow_prev, Annotation)
    assert a.arrow_prev.category == syntax.SEQUENCE_FLOW