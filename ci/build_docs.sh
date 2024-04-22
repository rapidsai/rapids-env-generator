#!/bin/bash
# Copyright (c) 2023-2024, NVIDIA CORPORATION.

set -euo pipefail

rapids-logger "Create test conda environment"
. /opt/conda/etc/profile.d/conda.sh

ENV_YAML_DIR="$(mktemp -d)"

rapids-dependency-file-generator \
  --output conda \
  --file_key docs \
  --matrix "" | tee "${ENV_YAML_DIR}/env.yaml"

rapids-mamba-retry env create --yes -f "${ENV_YAML_DIR}/env.yaml" -n docs
conda activate docs

rapids-print-env

rapids-logger "Downloading artifacts from previous jobs"
PYTHON_CHANNEL=$(rapids-download-conda-from-s3 python)

rapids-mamba-retry install \
  --channel "${PYTHON_CHANNEL}" \
  rapids-dependency-file-generator

export RAPIDS_DOCS_DIR="$(mktemp -d)"

rapids-logger "Build rapids-dependency-file-generator Sphinx docs"
pushd docs
make dirhtml
mkdir -p "${RAPIDS_DOCS_DIR}/rapids-dependency-file-generator/html"
mv build/dirhtml/* "${RAPIDS_DOCS_DIR}/rapids-dependency-file-generator/html"
if [[ "${RAPIDS_BUILD_TYPE}" != "pull-request" ]]; then
  make text
  mkdir -p "${RAPIDS_DOCS_DIR}/rapids-dependency-file-generator/txt"
  mv build/text/* "${RAPIDS_DOCS_DIR}/rapids-dependency-file-generator/txt"
fi
popd

rapids-upload-docs
