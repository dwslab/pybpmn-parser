import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Union

import yamlu
from yamlu.coco import Dataset
from yamlu.img import AnnotatedImage

from pybpmn.constants import ARROW_KEYPOINT_FIELDS, RELATIONS
from pybpmn.parser import BpmnParser
from pybpmn.syntax import (
    BPMNDI_EDGE_CATEGORIES,
    CATEGORY_GROUPS,
    CATEGORY_TO_LONG_NAME,
    EVENT_CATEGORY_TO_NO_POS_TYPE,
)
from pybpmn.util import split_img_id

_logger = logging.getLogger(__name__)


class HdBpmnDataset(Dataset):
    def __init__(
            self,
            hdbpmn_root: Union[Path, str],
            coco_dataset_root: Union[Path, str],
            category_translate_dict: Dict[str, str] = EVENT_CATEGORY_TO_NO_POS_TYPE,
            keypoint_fields: List[str] = ARROW_KEYPOINT_FIELDS,
            relation_fields: List[str] = RELATIONS,
            **parser_kwargs
    ):
        hdbpmn_root = Path(hdbpmn_root) if isinstance(hdbpmn_root, str) else hdbpmn_root
        assert hdbpmn_root.exists(), f"{hdbpmn_root} does not exist!"
        self.hdbpmn_root = hdbpmn_root.resolve() if not hdbpmn_root.is_absolute() else hdbpmn_root

        self.category_translate_dict = category_translate_dict

        self.split_to_bpmn_paths = self.get_split_to_bpmn_paths()
        self.img_id_to_bpmn_path = {p.stem: p for ps in self.split_to_bpmn_paths.values() for p in ps}

        self.bpmn_parser = BpmnParser(**parser_kwargs)
        super().__init__(
            dataset_path=coco_dataset_root,
            split_n_imgs={s: len(ps) for s, ps in self.split_to_bpmn_paths.items()},
            coco_categories=self._create_coco_categories(),
            keypoint_fields=keypoint_fields,
            relation_fields=relation_fields,
        )
        _logger.info(
            "Parsed hdBPMN dataset with %d images: %s",
            sum(self.split_n_imgs.values()),
            self.split_n_imgs,
        )

    def get_split_ann_img(self, split: str, idx: int) -> AnnotatedImage:
        bpmn_path = self.split_to_bpmn_paths[split][idx]
        return self.parse_bpmn_path(bpmn_path)

    def parse_bpmn_path(self, bpmn_path: Path):
        img_path = self.get_img_path(bpmn_path.stem)

        ai = self.bpmn_parser.parse_bpmn_img(bpmn_path, img_path)

        # "id" is reserved in coco, therefore use other field name
        for a in ai.annotations:
            if "id" in a:
                a.bpmn_id = a.id
            if a.category in self.category_translate_dict.keys():
                # noinspection PyPropertyAccess
                a.category = self.category_translate_dict[a.category]

        return ai

    @property
    def annotations_root(self):
        return self.hdbpmn_root / "data" / "annotations"

    @property
    def images_root(self):
        return self.hdbpmn_root / "data" / "images"

    def get_img_path(self, img_id: str):
        img_paths = yamlu.glob(self.images_root, f"*/{img_id}.*")
        assert len(img_paths) == 1, f"{img_id}: {img_paths}"
        return img_paths[0]

    def _get_all_bpmn_paths(self) -> List[Path]:
        bpmn_paths = yamlu.glob(self.annotations_root, "**/*.bpmn")
        assert len(bpmn_paths) > 0, f"Found no bpmn files under {self.annotations_root}"

        for bpmn_path in bpmn_paths:
            exercise, writer = split_img_id(bpmn_path.stem)
            assert exercise == bpmn_path.parent.name, f"{exercise} != {bpmn_path.name}"
        return bpmn_paths

    def _parse_writer_to_split(self) -> Dict[str, str]:
        csv_path = self.hdbpmn_root / "data" / "writer_split.csv"

        with csv_path.open() as f:
            # noinspection PyTypeChecker
            writer_to_split = dict(line.rstrip().split(",") for line in f)

        # delete header row
        del writer_to_split["writer"]

        return writer_to_split

    def get_split_to_bpmn_paths(self) -> Dict[str, List[Path]]:
        writer_to_split = self._parse_writer_to_split()

        split_to_bpmn_paths = defaultdict(list)
        bpmn_paths = self._get_all_bpmn_paths()
        for bpmn_path in bpmn_paths:
            exercise, writer = split_img_id(bpmn_path.stem)
            split = writer_to_split[writer]
            split_to_bpmn_paths[split].append(bpmn_path)

        return split_to_bpmn_paths

    def _create_coco_categories(self):
        seen_cats = set()

        i = 0
        coco_categories = []
        for supercategory, categories in CATEGORY_GROUPS.items():
            for category in categories:
                if category in self.bpmn_parser.excluded_categories:
                    continue
                category = self.category_translate_dict.get(category, category)
                if category in seen_cats:
                    continue
                seen_cats.add(category)

                coco_cat = {
                    "supercategory": supercategory,
                    "id": i,
                    "name": category,
                    "longname": CATEGORY_TO_LONG_NAME[category],
                }
                if category in BPMNDI_EDGE_CATEGORIES:
                    coco_cat["keypoints"] = ["head", "tail"]
                coco_categories.append(coco_cat)
                i += 1

        return coco_categories
