from pathlib import Path

from pybpmn.parser import BpmnParser


def test_parse_bpmn():
    resource_path = Path(__file__).resolve().parent / "resources"
    bpmn_path = resource_path / "process.bpmn"
    img_path = resource_path / "process.jpg"

    parser = BpmnParser()
    ai = parser.parse_bpmn_img(bpmn_path, img_path)
    assert len(ai.annotations) > 0
    assert ai.filename == img_path.name
