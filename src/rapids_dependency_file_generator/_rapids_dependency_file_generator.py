import fnmatch
import itertools
import os
import textwrap
import typing
from collections.abc import Generator
from dataclasses import dataclass

import tomlkit
import yaml

from . import _config
from ._constants import cli_name

__all__ = [
    "make_dependency_files",
]

HEADER = f"# This file is generated by `{cli_name}`."


def delete_existing_files(root: str) -> None:
    """Delete any files generated by this generator.

    This function can be used to clean up a directory tree before generating a new set
    of files from scratch.

    Parameters
    ----------
    root : str
        The path (relative or absolute) to the root of the directory tree to search for files to delete.
    """
    for dirpath, _, filenames in os.walk(root):
        for fn in filter(lambda fn: fn.endswith(".txt") or fn.endswith(".yaml"), filenames):
            with open(file_path := os.path.join(dirpath, fn)) as f:
                try:
                    if HEADER in f.read():
                        os.remove(file_path)
                except UnicodeDecodeError:
                    pass


def dedupe(
    dependencies: list[typing.Union[str, _config.PipRequirements]],
) -> typing.Sequence[typing.Union[str, dict[str, list[str]]]]:
    """Generate the unique set of dependencies contained in a dependency list.

    Parameters
    ----------
    dependencies : list[str | PipRequirements]
        A sequence containing dependencies (possibly including duplicates).

    Returns
    -------
    Sequence[str | dict[str, list[str]]]
        The ``dependencies`` with all duplicates removed.
    """
    string_deps: set[str] = set()
    pip_deps: set[str] = set()
    for dep in dependencies:
        if isinstance(dep, str):
            string_deps.add(dep)
        elif isinstance(dep, _config.PipRequirements):
            pip_deps.update(dep.pip)

    if pip_deps:
        return [*sorted(string_deps), {"pip": sorted(pip_deps)}]
    else:
        return sorted(string_deps)


def grid(gridspec: dict[str, list[str]]) -> Generator[dict[str, str], None, None]:
    """Yield the Cartesian product of a `dict` of iterables.

    The input ``gridspec`` is a dictionary whose keys correspond to
    parameter names. Each key is associated with an iterable of the
    values that parameter could take on. The result is a sequence of
    dictionaries where each dictionary has one of the unique combinations
    of the parameter values.

    Parameters
    ----------
    gridspec : dict[str, list[str]]
        A mapping from parameter names to lists of parameter values.

    Yields
    ------
    dict[str, str]
        Each yielded value is a dictionary containing one of the unique
        combinations of parameter values from `gridspec`.
    """
    for values in itertools.product(*gridspec.values()):
        yield dict(zip(gridspec.keys(), values))


def make_dependency_file(
    *,
    file_type: _config.Output,
    conda_env_name: typing.Union[str, None],
    file_name: str,
    config_file: os.PathLike,
    output_dir: os.PathLike,
    conda_channels: list[str],
    dependencies: typing.Sequence[typing.Union[str, dict[str, list[str]]]],
    extras: typing.Union[_config.FileExtras, None],
) -> str:
    """Generate the contents of the dependency file.

    Parameters
    ----------
    file_type : Output
        An Output value used to determine the file type.
    conda_env_name : str | None
        Name to put in the 'name: ' field when generating conda environment YAML files.
        If ``None``, the generated conda environment file will not have a 'name:' entry.
        Only used when ``file_type`` is CONDA.
    file_name : str
        Name of a file in ``output_dir`` to read in.
        Only used when ``file_type`` is PYPROJECT.
    config_file : PathLike
        The full path to the dependencies.yaml file.
    output_dir : PathLike
        The path to the directory where the dependency files will be written.
    conda_channels : list[str]
        The channels to include in the file. Only used when ``file_type`` is
        CONDA.
    dependencies : Sequence[str | dict[str, list[str]]]
        The dependencies to include in the file.
    extras : FileExtras | None
        Any extra information provided for generating this dependency file.

    Returns
    -------
    str
        The contents of the file.
    """
    relative_path_to_config_file = os.path.relpath(config_file, output_dir)
    file_contents = textwrap.dedent(
        f"""\
        {HEADER}
        # To make changes, edit {relative_path_to_config_file} and run `{cli_name}`.
        """
    )
    if file_type == _config.Output.CONDA:
        env_dict = {
            "channels": conda_channels,
            "dependencies": dependencies,
        }
        if conda_env_name is not None:
            env_dict["name"] = conda_env_name
        file_contents += yaml.dump(env_dict)
    elif file_type == _config.Output.REQUIREMENTS:
        for dep in dependencies:
            if isinstance(dep, dict):
                raise ValueError(f"Map inputs like {dep} are not allowed for the 'requirements' file type.")

            file_contents += f"{dep}\n"
    elif file_type == _config.Output.PYPROJECT:
        if extras is None:
            raise ValueError("The 'extras' field must be provided for the 'pyproject' file type.")

        if extras.table == "build-system":
            key = "requires"
            if extras.key is not None:
                raise ValueError(
                    "The 'key' field is not allowed for the 'pyproject' file type when 'table' is 'build-system'."
                )
        elif extras.table == "project":
            key = "dependencies"
            if extras.key is not None:
                raise ValueError(
                    "The 'key' field is not allowed for the 'pyproject' file type when 'table' is 'project'."
                )
        else:
            if extras.key is None:
                raise ValueError(
                    "The 'key' field is required for the 'pyproject' file type when "
                    "'table' is not one of 'build-system' or 'project'."
                )
            key = extras.key

        # This file type needs to be modified in place instead of built from scratch.
        with open(os.path.join(output_dir, file_name)) as f:
            file_contents_toml = tomlkit.load(f)

        toml_deps = tomlkit.array()
        for dep in dependencies:
            toml_deps.add_line(dep)
        toml_deps.add_line(indent="")
        toml_deps.comment(
            f"This list was generated by `{cli_name}`. To make changes, edit "
            f"{relative_path_to_config_file} and run `{cli_name}`."
        )

        # Recursively descend into subtables like "[x.y.z]", creating tables as needed.
        table = file_contents_toml
        for section in extras.table.split("."):
            try:
                table = table[section]
            except tomlkit.exceptions.NonExistentKey:
                # If table is not a super-table (i.e. if it has its own contents and is
                # not simply parted of a nested table name 'x.y.z') add a new line
                # before adding a new sub-table.
                if not table.is_super_table():
                    table.add(tomlkit.nl())
                table[section] = tomlkit.table()
                table = table[section]

        table[key] = toml_deps

        file_contents = tomlkit.dumps(file_contents_toml)

    return file_contents


def get_filename(file_type: _config.Output, file_key: str, matrix_combo: dict[str, str]):
    """Get the name of the file to which to write a generated dependency set.

    The file name will be composed of the following components, each determined
    by the `file_type`:
        - A file-type-based prefix e.g. "requirements" for requirements.txt files.
        - A name determined by the value of $FILENAME in the corresponding
          [files.$FILENAME] section of dependencies.yaml. This name is used for some
          output types (conda, requirements) and not others (pyproject).
        - A matrix description encoding the key-value pairs in `matrix_combo`.
        - A suitable extension for the file (e.g. ".yaml" for conda environment files.)

    Parameters
    ----------
    file_type : Output
        An Output value used to determine the file type.
    file_key : str
        The name of this member in the [files] list in dependencies.yaml.
    matrix_combo : dict[str, str]
        A mapping of key-value pairs corresponding to the
        [files.$FILENAME.matrix] entry in dependencies.yaml.

    Returns
    -------
    str
        The name of the file to generate.
    """
    file_type_prefix = ""
    file_ext = ""
    file_name_prefix = file_key
    suffix = "_".join([f"{k}-{v}" for k, v in matrix_combo.items()])
    if file_type == _config.Output.CONDA:
        file_ext = ".yaml"
    elif file_type == _config.Output.REQUIREMENTS:
        file_ext = ".txt"
        file_type_prefix = "requirements"
    elif file_type == _config.Output.PYPROJECT:
        file_ext = ".toml"
        # Unlike for files like requirements.txt or conda environment YAML files, which
        # may be named with additional prefixes (e.g. all_cuda_*) pyproject.toml files
        # need to have that exact name and are never prefixed.
        file_name_prefix = "pyproject"
        suffix = ""
    filename = "_".join(filter(None, (file_type_prefix, file_name_prefix, suffix))).replace(".", "")
    return filename + file_ext


def get_output_dir(*, file_type: _config.Output, config_file_path: os.PathLike, file_config: _config.File):
    """Get the directory containing a generated dependency file's contents.

    The output directory is determined by the `file_type` and the corresponding
    key in the `file_config`. The path provided in `file_config` will be taken
    relative to `output_root`.

    Parameters
    ----------
    file_type : Output
        An Output value used to determine the file type.
    config_file_path : PathLike
        Path to the dependency-file-generator config file (e.g. dependencies.yaml).
    file_config : File
        A dictionary corresponding to one of the [files.$FILENAME] sections of
        the dependencies.yaml file. May contain `conda_dir`, `pyproject_dir`, or `requirements_dir`.

    Returns
    -------
    str
        The directory containing the dependency file's contents.
    """
    path = [os.path.dirname(config_file_path)]
    if file_type == _config.Output.CONDA:
        path.append(file_config.conda_dir)
    elif file_type == _config.Output.REQUIREMENTS:
        path.append(file_config.requirements_dir)
    elif file_type == _config.Output.PYPROJECT:
        path.append(file_config.pyproject_dir)
    return os.path.join(*path)


def should_use_specific_entry(matrix_combo: dict[str, str], specific_entry_matrix: dict[str, str]) -> bool:
    """Check if an entry should be used.

    Dependencies listed in the [dependencies.$DEPENDENCY_GROUP.specific]
    section are specific to a particular matrix entry provided by the
    [matrices] list. This function validates the [matrices.matrix] value
    against the provided `matrix_combo` to check if they are compatible.

    A `specific_entry_matrix` is compatible with a `matrix_combo` if and only
    if `specific_entry_matrix[key]` matches the glob pattern
    `matrix_combo[key]` for every key defined in `specific_entry_matrix`. A
    `matrix_combo` may contain additional keys not specified by
    `specific_entry_matrix`.

    Parameters
    ----------
    matrix_combo : dict[str, str]
        A mapping from matrix keys to values for the current file being
        generated.
    specific_entry_matrix : dict[str, str]
        A mapping from matrix keys to values for the current specific
        dependency set being checked.

    Returns
    -------
    bool
        True if the `specific_entry_matrix` is compatible with the current
        `matrix_combo` and False otherwise.
    """
    return all(
        specific_key in matrix_combo and fnmatch.fnmatch(matrix_combo[specific_key], specific_value)
        for specific_key, specific_value in specific_entry_matrix.items()
    )


@dataclass
class _DependencyCollection:
    str_deps: set[str]
    # e.g. {"pip": ["dgl", "pyg"]}, used in conda envs
    dict_deps: dict[str, list[str]]

    def update(self, deps: typing.Sequence[typing.Union[str, dict[str, list[str]]]]) -> None:
        for dep in deps:
            if isinstance(dep, dict):
                for k, v in dep.items():
                    if k in self.dict_deps:
                        self.dict_deps[k].extend(v)
                        self.dict_deps[k] = sorted(set(self.dict_deps[k]))
                    else:
                        self.dict_deps[k] = v
            else:
                self.str_deps.add(dep)

    @property
    def deps_list(self) -> typing.Sequence[typing.Union[str, dict[str, list[str]]]]:
        if self.dict_deps:
            return [*sorted(self.str_deps), self.dict_deps]

        return [*sorted(self.str_deps)]


def make_dependency_files(
    *,
    parsed_config: _config.Config,
    file_keys: list[str],
    output: typing.Union[set[_config.Output], None],
    matrix: typing.Union[dict[str, list[str]], None],
    prepend_channels: list[str],
    to_stdout: bool,
) -> None:
    """Generate dependency files.

    This function iterates over data parsed from a YAML file conforming to the
    `dependencies.yaml file spec <https://github.com/rapidsai/dependency-file-generator#dependenciesyaml-format>`_
    and produces the requested files.

    Parameters
    ----------
    parsed_config : Config
        The parsed dependencies.yaml config file.
    file_keys : list[str]
        The list of file keys to use.
    output : set[Output] | None
        The set of file types to write, or None to write the file types
        specified by the file key.
    matrix : dict[str, list[str]] | None
        The matrix to use, or None if the default matrix from each file key
        should be used.
    prepend_channels : list[str]
        List of channels to prepend to the ones from parsed_config.
    to_stdout : bool
        Whether the output should be written to stdout. If False, it will be
        written to a file computed based on the output file type and
        config_file_path.

    Raises
    ------
    ValueError
        If the file is malformed. There are numerous different error cases
        which are described by the error messages.
    """
    if to_stdout and len(file_keys) > 1 and output is not None and _config.Output.PYPROJECT in output:
        raise ValueError(
            f"Using --file-key multiple times together with '--output {_config.Output.PYPROJECT.value}' "
            "when writing to stdout is not supported."
        )

    # the list of conda channels does not depend on individual file keys
    conda_channels = prepend_channels + parsed_config.channels

    # initialize a container for "all dependencies found across all files", to support
    # passing multiple files keys and writing a merged result to stdout
    all_dependencies = _DependencyCollection(str_deps=set(), dict_deps={})

    for file_key in file_keys:
        file_config = parsed_config.files[file_key]
        file_types_to_generate = file_config.output if output is None else output
        if matrix is not None:
            file_matrix = matrix
        else:
            file_matrix = file_config.matrix
        calculated_grid = list(grid(file_matrix))
        if _config.Output.PYPROJECT in file_types_to_generate and len(calculated_grid) > 1:
            raise ValueError("Pyproject outputs can't have more than one matrix output")
        for file_type in file_types_to_generate:
            for matrix_combo in calculated_grid:
                dependencies = []

                # Collect all includes from each dependency list corresponding
                # to this (file_name, file_type, matrix_combo) tuple. The
                # current tuple corresponds to a single file to be written.
                for include in file_config.includes:
                    dependency_entry = parsed_config.dependencies[include]

                    for common_entry in dependency_entry.common:
                        if file_type not in common_entry.output_types:
                            continue
                        dependencies.extend(common_entry.packages)

                    for specific_entry in dependency_entry.specific:
                        if file_type not in specific_entry.output_types:
                            continue

                        # Ensure that all specific matrices are unique
                        num_matrices = len(specific_entry.matrices)
                        num_unique = len(
                            {
                                frozenset(specific_matrices_entry.matrix.items())
                                for specific_matrices_entry in specific_entry.matrices
                            }
                        )
                        if num_matrices != num_unique:
                            err = f"All matrix entries must be unique. Found duplicates in '{include}':"
                            for specific_matrices_entry in specific_entry.matrices:
                                err += f"\n - {specific_matrices_entry.matrix}"
                            raise ValueError(err)

                        fallback_entry = None
                        for specific_matrices_entry in specific_entry.matrices:
                            # An empty `specific_matrices_entry["matrix"]` is
                            # valid and can be used to specify a fallback_entry for a
                            # `matrix_combo` for which no specific entry
                            # exists. In that case we save the fallback_entry result
                            # and only use it at the end if nothing more
                            # specific is found.
                            if not specific_matrices_entry.matrix:
                                fallback_entry = specific_matrices_entry
                                continue

                            if should_use_specific_entry(matrix_combo, specific_matrices_entry.matrix):
                                # A package list may be empty as a way to
                                # indicate that for some matrix elements no
                                # packages should be installed.
                                dependencies.extend(specific_matrices_entry.packages or [])
                                break
                        else:
                            if fallback_entry:
                                dependencies.extend(fallback_entry.packages)
                            else:
                                raise ValueError(f"No matching matrix found in '{include}' for: {matrix_combo}")

                # Dedupe deps and print / write to filesystem
                full_file_name = get_filename(file_type, file_key, matrix_combo)
                deduped_deps = dedupe(dependencies)

                output_dir = get_output_dir(
                    file_type=file_type,
                    config_file_path=parsed_config.path,
                    file_config=file_config,
                )
                contents = make_dependency_file(
                    file_type=file_type,
                    conda_env_name=os.path.splitext(full_file_name)[0],
                    file_name=full_file_name,
                    config_file=parsed_config.path,
                    output_dir=output_dir,
                    conda_channels=conda_channels,
                    dependencies=deduped_deps,
                    extras=file_config.extras,
                )

                if to_stdout:
                    if len(file_keys) == 1:
                        print(contents)
                    else:
                        all_dependencies.update(deduped_deps)
                else:
                    os.makedirs(output_dir, exist_ok=True)
                    file_path = os.path.join(output_dir, full_file_name)
                    with open(file_path, "w") as f:
                        f.write(contents)

    # create one unified output from all the file_keys, and print it to stdout
    if to_stdout and len(file_keys) > 1:
        # convince mypy that 'output' is not None here
        #
        # 'output' is technically a set because of https://github.com/rapidsai/dependency-file-generator/pull/74,
        # but since https://github.com/rapidsai/dependency-file-generator/pull/79 it's only ever one of the following:
        #
        #   - an exactly-1-item set (stdout=True, or when used by rapids-build-backend)
        #   - 'None' (stdout=False)
        #
        err_msg = (
            "Exactly 1 output type should be provided when asking rapids-dependency-file-generator to write to stdout. "
            "If you see this, you've found a bug. Please report it."
        )
        assert output is not None, err_msg

        contents = make_dependency_file(
            file_type=output.pop(),
            conda_env_name=None,
            file_name="ignored-because-multiple-pyproject-files-are-not-supported",
            config_file=parsed_config.path,
            output_dir=parsed_config.path,
            conda_channels=conda_channels,
            dependencies=all_dependencies.deps_list,
            extras=None,
        )
        print(contents)
