![run_tests workflow](https://github.com/dwslab/pybpmn-parser/actions/workflows/run_tests.yaml/badge.svg)
[![PyPI-Server](https://img.shields.io/pypi/v/pybpmn-parser.svg)](https://pypi.org/project/pybpmn-parser/)

# pybpmn-parser

Starter code for using the [hdBPMN] dataset for diagram recognition research.

The [dump_coco.py](./scripts/dump_coco.py) script can be used to convert the images and BPMN XMLs into a [COCO] dataset.
COCO is a common format used in computer vision research to annotate the objects and keypoints in images.
```shell
python scripts/dump_coco.py path/to/hdBPMN path/to/target/coco/directory/hdbpmn
```

Moreover, the [demo.ipynb](./notebooks/demo.ipynb) Jupyter notebook can be used to visualize
(1) the extracted bounding boxes, keypoints, and relations,
and (2) the annotated BPMN diagram overlayed over the hand-drawn image.
Note that the latter requires the [bpmn-to-image] tool, which in turn requires a nodejs installation.

## Installation

```shell
pip install pybpmn-parser
```

## Development

In order to set up the necessary environment:

1. create an environment `pybpmn-parser` with the help of [conda]:
   ```
   conda env create -f environment.yml
   ```
2. activate the new environment with:
   ```
   conda activate pybpmn-parser
   ```
   
> **_NOTE:_**  The conda environment will have pybpmn-parser installed in editable mode.
> Some changes, e.g. in `setup.cfg`, might require you to run `pip install -e .` again.


Optional and needed only once after `git clone`:

3. install JupyterLab kernel
   ```
   python -m ipykernel install --user --name "${CONDA_DEFAULT_ENV}" --display-name "$(python -V) (${CONDA_DEFAULT_ENV})"
   ```

4. install several [pre-commit] git hooks with:
   ```bash
   pre-commit install
   # You might also want to run `pre-commit autoupdate`
   ```
   and checkout the configuration under `.pre-commit-config.yaml`.
   The `-n, --no-verify` flag of `git commit` can be used to deactivate pre-commit hooks temporarily.

## Dependency Management & Reproducibility

1. Always keep your abstract (unpinned) dependencies updated in `environment.yml` and eventually
   in `setup.cfg` if you want to ship and install your package via `pip` later on.
2. Create concrete dependencies as `environment.lock.yml` for the exact reproduction of your
   environment with:
   ```bash
   conda env export -n pybpmn-parser -f environment.lock.yml
   ```
   For multi-OS development, consider using `--no-builds` during the export.
3. Update your current environment with respect to a new `environment.lock.yml` using:
   ```bash
   conda env update -f environment.lock.yml --prune
   ```
## Project Organization

```
├── LICENSE.txt             <- License as chosen on the command-line.
├── README.md               <- The top-level README for developers.
├── data
│   ├── external            <- Data from third party sources.
│   ├── interim             <- Intermediate data that has been transformed.
│   ├── processed           <- The final, canonical data sets for modeling.
│   └── raw                 <- The original, immutable data dump.
├── docs                    <- Directory for Sphinx documentation in rst or md.
├── environment.yml         <- The conda environment file for reproducibility.
├── notebooks               <- Jupyter notebooks. Naming convention is a number (for
│                              ordering), the creator's initials and a description,
│                              e.g. `1.0-fw-initial-data-exploration`.
├── pyproject.toml          <- Build system configuration. Do not change!
├── scripts                 <- Analysis and production scripts which import the
│                              actual Python package, e.g. train_model.py.
├── setup.cfg               <- Declarative configuration of your project.
├── setup.py                <- Use `pip install -e .` to install for development or
│                              or create a distribution with `tox -e build`.
├── src
│   └── pybpmn              <- Actual Python package where the main functionality goes.
├── tests                   <- Unit tests which can be run with `py.test`.
├── .coveragerc             <- Configuration for coverage reports of unit tests.
├── .isort.cfg              <- Configuration for git hook that sorts imports.
└── .pre-commit-config.yaml <- Configuration of pre-commit git hooks.
```

<!-- pyscaffold-notes -->

## Note

This project has been set up using [PyScaffold] 4.0.1 and the [dsproject extension] 0.6.1.

[conda]: https://docs.conda.io/
[pre-commit]: https://pre-commit.com/
[Jupyter]: https://jupyter.org/
[nbstripout]: https://github.com/kynan/nbstripout
[Google style]: http://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings
[PyScaffold]: https://pyscaffold.org/
[dsproject extension]: https://github.com/pyscaffold/pyscaffoldext-dsproject
[bpmn-to-image]: https://github.com/bpmn-io/bpmn-to-image
[COCO]: https://cocodataset.org/#format-data
[hdBPMN]: https://github.com/dwslab/hdBPMN
