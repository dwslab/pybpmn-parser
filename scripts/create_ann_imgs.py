import os
from pathlib import Path

import click
import yamlu

from pybpmn.parser import BpmnParser, InvalidBpmnException

@click.command()
@click.argument("dataset_root", type=click.Path(file_okay=False, exists=True))
def main(dataset_root: str):

    # (i) Get all available annotation paths with img path that do not have an annotated img already
    dataset_root = Path(dataset_root)
    anns_root = dataset_root / "annotations"
    bpmn_paths = yamlu.glob(anns_root, "**/*.bpmn")

    imgs_root = dataset_root / "images"
    imgs_ann_root = dataset_root / "images-annotated"
    valid_bpmn_to_img_path = {}
    for bpmn_path in bpmn_paths:
        img_paths = yamlu.glob(imgs_root, f"{bpmn_path.stem}.*")
        ann_img_exists = os.path.exists(imgs_ann_root / f"{bpmn_path.stem}.jpg")
        if len(img_paths) > 0 and not ann_img_exists:
            valid_bpmn_to_img_path[bpmn_path] = img_paths[0]
    
    print(f"Found {len(valid_bpmn_to_img_path)} annotation files with images that don't have an annotated image already")

    # (ii) Parse to annotated img
    bpmn_parser = BpmnParser(scale_to_ann_width=False)
    for bpmn_path, img_path in valid_bpmn_to_img_path.items():
        try:
            ann_img = bpmn_parser.parse_bpmn_img(bpmn_path, img_path)
            ann_img.save_with_anns(imgs_ann_root, suffix="")
            print(f"Created annotated img of {bpmn_path.stem}")
        except InvalidBpmnException as e:
            print(f"{e.error_type}, {e.details} in diagram {bpmn_path.stem}")

if __name__ == "__main__":
    main()