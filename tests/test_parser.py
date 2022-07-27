from pathlib import Path

from pybpmn.parser import BpmnParser

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
