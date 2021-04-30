#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import sys
from typing import List, Optional

import click
from IPython.core import ultratb
from yamlu.coco import CocoDatasetExport

import pybpmn
from pybpmn.constants import VALID_SPLITS
from pybpmn.dataset import HdBpmnDataset

# fallback to debugger on error
sys.excepthook = ultratb.FormattedTB(mode="Verbose", color_scheme="Linux", call_pdb=1)

_logger = logging.getLogger(__name__)


@click.command()
@click.argument("hdbpmn_root", type=click.Path(file_okay=False, exists=True))
@click.argument("coco_dataset_root", type=click.Path(file_okay=False))
@click.option("--sample", default=None, type=int)
@click.option("--n_jobs", default=None, type=int)
@click.option("--write_img", default=True, type=bool)
@click.option("--write_ann_img", default=False, type=bool)
@click.option("--splits", "-s", multiple=True, default=list(VALID_SPLITS))
@click.option("--quiet", "log_level", flag_value=logging.WARNING)
@click.option("-v", "--verbose", "log_level", flag_value=logging.INFO, default=True)
@click.option("-vv", "--very-verbose", "log_level", flag_value=logging.DEBUG)
@click.version_option(pybpmn.__version__)
def main(
        hdbpmn_root: str,
        coco_dataset_root: str,
        sample: Optional[int],
        n_jobs: Optional[int],
        write_img: bool,
        write_ann_img: bool,
        splits: List[str],
        log_level: int,
):
    logging.basicConfig(format="%(asctime)s %(levelname)s - %(message)s", level=log_level)
    # logging.getLogger("yamlu.img").setLevel(logging.ERROR)

    ds = HdBpmnDataset(hdbpmn_root=hdbpmn_root, coco_dataset_root=coco_dataset_root)

    exporter = CocoDatasetExport(
        ds=ds,
        write_img=write_img,
        write_ann_img=write_ann_img,
        sample=sample,
        n_jobs=n_jobs,
    )
    for split in splits:
        exporter.dump_split(split)


if __name__ == "__main__":
    main()
