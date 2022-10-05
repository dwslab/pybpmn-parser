import click
import os
import yamlu
from yamlu.img import AnnotatedImage
from pathlib import Path
from pybpmn.parser import BpmnParser

@click.command()
@click.argument("dataset_root", type=click.Path(file_okay=False, exists=True))
def main(dataset_root: str):

    # (i) Get all available annotation paths with img path that do not have an annotated img already
    dataset_root = Path(dataset_root)
    anns_root = dataset_root / "annotations"
    bpmn_paths = yamlu.glob(anns_root, "**/*.bpmn")

    imgs_root = dataset_root / "images"
    imgs_ann_root = dataset_root / "images-annotated"
    valid_anns_imgs_paths = []
    for bpmn_path in bpmn_paths:
        img_paths = yamlu.glob(imgs_root, f"{bpmn_path.stem}.*")
        ann_img_exists_already = os.path.exists(imgs_ann_root / f"{bpmn_path.stem}_bb.jpg")
        if (len(img_paths) > 0 and not ann_img_exists_already):
            valid_anns_imgs_paths.append({"bpmn_path": bpmn_path, "img_path": img_paths[0]})
    
    print(f"Found {len(valid_anns_imgs_paths)} annotation files with images that don't have an annotated image already")

    # (ii) Parse to annotated img
    bpmn_parser = BpmnParser()
    for ann_img_path in valid_anns_imgs_paths:
        ann_img = bpmn_parser.parse_bpmn_img(ann_img_path["bpmn_path"], ann_img_path["img_path"], False)
        ann_img.save_with_anns(imgs_ann_root)
        print(f"Created annotated img of {ann_img_path['bpmn_path'].stem}")

if __name__ == "__main__":
    main()