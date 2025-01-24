# rapids-dependency-file-generator

`rapids-dependency-file-generator` is a Python CLI tool that generates conda `environment.yaml` files and `requirements.txt` files from a single YAML file, typically named `dependencies.yaml`.

When installed, it makes the `rapids-dependency-file-generator` CLI command available which is responsible for parsing a `dependencies.yaml` configuration file and generating the appropriate conda `environment.yaml` and `requirements.txt` dependency files.

## Installation

`rapids-dependency-file-generator` is available on [PyPI](https://pypi.org/project/rapids-dependency-file-generator/). To install, run:

```sh
pip install rapids-dependency-file-generator
```

## Usage

When `rapids-dependency-file-generator` is invoked, it will read a `dependencies.yaml` file from the current directory and generate children dependency files.

The `dependencies.yaml` file has the following characteristics:

- it is intended to be committed to the root directory of repositories
- it can define matrices that enable the output dependency files to vary according to any arbitrary specification (or combination of specifications), including CUDA version, machine architecture, Python version, etc.
- it contains bifurcated lists of dependencies based on the dependency's purpose (i.e. build, runtime, test, etc.). The bifurcated dependency lists are merged according to the description in the _"How Dependency Lists Are Merged"_ section below.

## `dependencies.yaml` Format

The `dependencies.yaml` file has three relevant top-level keys: `files`, `channels`, and `dependencies`. These keys are described in detail below.

### `files` Key

The top-level `files` key is responsible for determining the following:

- which types of dependency files should be generated (i.e. conda `environment.yaml` files and/or `requirements.txt` files)
- where the generated files should be written to (relative to the `dependencies.yaml` file)
- which variant files should be generated (based on the provided matrix)
- which of the dependency lists from the top-level `dependencies` key should be included in the generated files

Here is an example of what the `files` key might look like:

```yaml
files:
  all: # used as the prefix for the generated dependency file names for conda or requirements files (has no effect on pyproject.toml files)
    output: [conda, requirements] # which dependency file types to generate. required, can be "conda", "requirements", "pyproject", "none" or a list of non-"none" values
    conda_dir: conda/environments # where to put conda environment.yaml files. optional, defaults to "conda/environments"
    requirements_dir: python/cudf # where to put requirements.txt files. optional, but recommended. Used for devcontainers. defaults to "python"
    pyproject_dir: python/cudf # where to put pyproject.toml files. optional, but recommended. Used for wheel builds. defaults to "python"
    matrix: # (optional) contains an arbitrary set of key/value pairs to determine which dependency files that should be generated. These values are included in the output filename.
      cuda: ["11.5", "11.6"] # which CUDA version variant files to generate.
      arch: [x86_64] # which architecture version variant files to generate. This value should be the result of running the `arch` command on a given machine.
    includes: # a list of keys from the `dependencies` section which should be included in the generated files
      - build
      - test
      - runtime
  build: # multiple `files` children keys can be specified
    output: requirements
    conda_dir: conda/environments
    requirements_dir: python/cudf
    matrix:
      cuda: ["11.5"]
      arch: [x86_64]
      py: ["3.8"]
    includes:
      - build
```

The result of the above configuration is that the following dependency files would be generated:

- `conda/environments/all_cuda-115_arch-x86_64.yaml`
- `conda/environments/all_cuda-116_arch-x86_64.yaml`
- `python/cudf/requirements_all_cuda-115_arch-x86_64.txt`
- `python/cudf/requirements_all_cuda-116_arch-x86_64.txt`
- `python/cudf/requirements_build_cuda-115_arch-x86_64_py-38.txt`

The `all*.yaml` and `requirements_all*.txt` files would include the contents of the `build`, `test`, and `runtime` dependency lists from the top-level `dependency` key. The `requirements_build*.txt` file would only include the contents of the `build` dependency list from the top-level `dependency` key.

The value of `output` can also be `none` as shown below.

```yaml
files:
  test:
    output: none
    includes:
      - test
```

When `output: none` is used, the `conda_dir`, `requirements_dir` and `matrix` keys can be omitted. The use case for `output: none` is described in the [_Additional CLI Notes_](#additional-cli-notes) section below.

If more than one `files` key specifies the same output and *_dir, their contents are merged. This is how different sections are written to a given output file.

#### `extras`

A given file may include an `extras` entry that may be used to provide inputs specific to a particular file type

Here is an example:

```yaml
files:
  build:
    output: pyproject
    extras:
      table: table_name
      key: key_name
```

Currently the supported extras by file type are:
- pyproject.toml
  - table: The table in pyproject.toml where the dependencies should be written. Acceptable values are "build-system", "project", "project.optional-dependencies", and "tool.rapids-build-backend"
  - key: The key corresponding to the dependency list in `table`. This may only be provided for the "project.optional-dependencies" or "tool.rapids-build-backend" table since the key name is fixed for "build-system" ("requires") and "project" ("dependencies"). Note that this implicitly prohibits including optional dependencies via an inline table under the "project" table.

### `channels` Key

The top-level `channels` key specifies the channels that should be included in any generated conda `environment.yaml` files.

It might look like this:

```yaml
channels:
  - rapidsai
  - conda-forge
```

In the absence of a `channels` key, some sensible defaults for RAPIDS will be used (see [constants.py](./src/rapids_dependency_file_generator/constants.py)).

### `dependencies` Key

The top-level `dependencies` key is where the bifurcated dependency lists should be specified.

Underneath the `dependencies` key are sets of key-value pairs. For each pair, the key can be arbitrarily named, but should match an item from the `includes` list of any `files` entry.

The value of each key-value pair can have the following children keys:

- `common` - contains dependency lists that are the same across all matrix variations
- `specific` - contains dependency lists that are specific to a particular matrix combination

The values of each of these keys are described in detail below.

#### `common` Key

The `common` key contains a list of objects with the following keys:

- `output_types` - a list of output types (e.g. "conda" for `environment.yaml` files or "requirements" for `requirements.txt` files) for the packages in the `packages` key
- `packages` - a list of packages to be included in the generated output file

#### `specific` Key

The `specific` key contains a list of objects with the following keys:

- `output_types` - _same as `output_types` for the `common` key above_
- `matrices` - a list of objects (described below) which define packages that are specific to a particular matrix combination

##### `matrices` Key

Each list item under the `matrices` key contains a `matrix` key and a `packages` key.
The `matrix` key is used to define which matrix combinations from `files.[*].matrix` will use the associated packages.
The `packages` key is a list of packages to be included in the generated output file for a matching matrix.
This is elaborated on in [How Dependency Lists Are Merged](#how-dependency-lists-are-merged).

An example of the above structure is exemplified below:

```yaml
dependencies:
  build: # dependency list name
    common: # dependencies common among all matrix variations
      - output_types: [conda, requirements] # the output types this list item should apply to
        packages:
          - common_build_dep
      - output_types: conda
        packages:
          - cupy
          - pip: # supports `pip` key for conda environment.yaml files
              - some_random_dep
    specific: # dependencies specific to a particular matrix combination
      - output_types: conda # dependencies specific to conda environment.yaml files
        matrices:
          - matrix:
              cuda: "11.5"
            packages:
              - cudatoolkit=11.5
          - matrix:
              cuda: "11.6"
            packages:
              - cudatoolkit=11.6
          - matrix: # an empty matrix entry serves as a fallback if there are no other matrix matches
            packages:
              - cudatoolkit
      - output_types: [conda, requirements]
        matrices:
          - matrix: # dependencies specific to x86_64 and 11.5
              cuda: "11.5"
              arch: x86_64
            packages:
              - a_random_x86_115_specific_dep
          - matrix: # an empty matrix/package entry to prevent error from being thrown for non 11.5 and x86_64 matches
            packages:
      - output_types: requirements # dependencies specific to requirements.txt files
        matrices:
          - matrix:
              cuda: "11.5"
            packages:
              - another_random_dep=11.5.0
          - matrix:
              cuda: "11.6"
            packages:
              - another_random_dep=11.6.0
  test:
    common:
      - output_types: [conda, requirements]
        packages:
          - pytest
```

## Naming conventions

With non-trivial collections of files and dependencies, names can look very related and become hard to distinguish. Some general guidelines that will help keep things more understandable:

### Patterns for [RAPIDS build backend](https://github.com/rapidsai/rapids-build-backend)

RBB builds generally include at least two sections:

```
files:
  # This dependency brings in RBB
  py_build_<something>:
    output: pyproject
    extras:
      table: build-system  # This is the thing to match with the py_build_* name
    includes:
      - <rapids_build_skbuild>
  # This dependency expresses the build-time dependencies for your recipe (what might otherwise go in [build-system] when not using RBB)
  py_rapids_build_<something>:
    output: pyproject
    extras:
      table: tool.rapids-build-backend  # This is the thing to match with the py_rapids_build_* name
      key: requires
    includes:
      - <normal_project_build_time_deps>
```

### Patterns for dependencies

To help distinguish dependency specifications from file specifications, it is recommended to prefix dependency entries
with `dep_<type>_<name>`, where type is one of `build`, `run`, or `test`. This is functionally superfluous, as the `extras.table`
value will ultimately determine where the dependency entries will go, but following the convention will make your dependencies.yaml
file easier to follow.

## How Dependency Lists Are Merged

The information from the top-level `files` and `dependencies` keys are used to determine which dependencies should be included in the final output of the generated dependency files.

Consider the following top-level `files` key configuration:

```yaml
files:
  all:
    output: conda
    conda_dir: conda/environments
    requirements_dir: python/cudf
    matrix:
      cuda: ["11.5", "11.6"]
      arch: [x86_64]
    includes:
      - build
      - test
```

In this example, `rapids-dependency-file-generator` will generate two conda environment files: `conda/environments/all_cuda-115_arch-x86_64.yaml` and `conda/environments/all_cuda-116_arch-x86_64.yaml`.

Since the `output` value is `conda`, `rapids-dependency-file-generator` will iterate through any `dependencies.build.common` and `dependencies.test.common` list entries and use the `packages` of any entry whose `output_types` key is `conda` or `[conda, ...]`.

Further, for the `11.5` and `x86_64` matrix combination, any `build.specific` and `test.specific` list items whose output includes `conda` and whose `matrices` list items matches any of the definitions below would also be merged:

```yaml
specific:
  - output_types: conda
    matrices:
      - matrix:
          cuda: "11.5"
        packages:
          - some_dep1
          - some_dep2
# or
specific:
  - output_types: conda
    matrices:
      - matrix:
          cuda: "11.5"
          arch: "x86_64"
        packages:
          - some_dep1
          - some_dep2
# or
specific:
  - output_types: conda
    matrices:
      - matrix:
          arch: "x86_64"
        packages:
          - some_dep1
          - some_dep2
```

Every `matrices` list must have a match for a given input matrix (only the first matching matrix in the list of `matrices` will be used).
If no matches are found for a particular matrix combination, an error will be thrown.
In instances where an error should not be thrown, an empty `matrix` and `packages` list item can be used:

```yaml
- output_types: conda
  matrices:
    - matrix:
        cuda: "11.5"
        arch: x86_64
        py: "3.8"
      packages:
        - a_very_specific_115_x86_38_dep
    - matrix: # an empty matrix entry serves as a fallback if there are no other matrix matches
      packages:
```

Merged dependency lists are sorted and deduped.

## Additional CLI Notes

Invoking `rapids-dependency-file-generator` without any arguments is meant to be the default behavior for RAPIDS developers. It will generate all of the necessary dependency files as specified in the top-level `files` configuration.

However, there are CLI arguments that can augment the `files` configuration values before the files are generated.

Consider the example when `output: none` is used:

```yaml
files:
  test:
    output: none
    includes:
      - test
```

The `test` file generated by the configuration above is useful for CI, but it might not make sense to necessarily commit those files to a repository. In such a scenario, the following CLI arguments can be used:

```sh
ENV_NAME="cudf_test"

rapids-dependency-file-generator \
  --file-key "test" \
  --output "conda" \
  --matrix "cuda=12.5;arch=$(arch)" > env.yaml
mamba env create --file env.yaml
mamba activate "$ENV_NAME"

# install cudf packages built in CI and test them in newly created environment...
```

The `--file-key` argument is passed the `test` key name from the `files` configuration. Additional flags are used to generate a single dependency file. When the CLI is used in this fashion, it will print to `stdout` instead of writing the resulting contents to the filesystem.

The `--file-key`, `--output`, and `--matrix` flags must be used together. `--matrix` may be an empty string if the file that should be generated does not depend on any specific matrix variations.

Where multiple values for the same key are passed to `--matrix`, e.g. `cuda_suffixed=true;cuda_suffixed=false`, only the last value will be used.

Where `--file-key` is supplied multiple times in the same invocation, the output printed to `stdout` will contain a union (without duplicates) of all of the corresponding dependencies. For example:

```shell
rapids-dependency-file-generator \
  --file-key "test" \
  --file-key "test_notebooks" \
  --output "conda" \
  --matrix "cuda=12.5;arch=$(arch)" > env.yaml
```

The `--prepend-channel` argument accepts additional channels to use, like `rapids-dependency-file-generator --prepend-channel my_channel --prepend-channel my_other_channel`.
If both `--output` and `--prepend-channel` are provided, the output format must be conda.
Prepending channels can be useful for adding local channels with packages to be tested in CI workflows.

Running `rapids-dependency-file-generator -h` will show the most up-to-date CLI arguments.
