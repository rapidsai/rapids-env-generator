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

rapids-mamba-retry install \
  --channel "file://$(pwd)/artifacts-channel" \
  rapids-dependency-file-generator

rapids-logger "Build rapids-dependency-file-generator Sphinx docs"
pushd docs
make dirhtml
mkdir -p "${OUTPUT_DIR}/rapids-dependency-file-generator/html"
mv build/dirhtml/* "${OUTPUT_DIR}/rapids-dependency-file-generator/html"
make text
mkdir -p "${OUTPUT_DIR}/rapids-dependency-file-generator/txt"
mv build/text/* "${OUTPUT_DIR}/rapids-dependency-file-generator/txt"
popd
