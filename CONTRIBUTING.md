# Contributing

## Releases

Releases for `dependency-file-generator` are handled by [semantic-release][semantic-release]. To ensure that every commit on the `main` branch has a semantic commit message, the following settings have been configured:

- Only squash commits are allowed
- The default squash commit message is derived from the pull-request's title and body
- Pull request titles are required to be semantic commit messages

The table below (from [semantic-release][semantic-release] docs) shows the types of changes that correspond to each release type.

| Commit message                                                                                                                                                                                   | Release type                                                                                    |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| `fix(pencil): stop graphite breaking when too much pressure applied`                                                                                                                             | Patch Release                                                                                   |
| `feat(pencil): add 'graphiteWidth' option`                                                                                                                                                       | Minor Release                                                                                   |
| `perf(pencil): remove graphiteWidth option`<br><br>`BREAKING CHANGE: The graphiteWidth option has been removed.`<br>`The default graphite width of 10mm is always used for performance reasons.` | Major <br /> (Note that the `BREAKING CHANGE: ` string must be in the body of the pull-request) |

If a change type not listed in the table above is used, it will not trigger a release. For example:

- `docs: fix README type`
- `ci: update GHAs workflow`
- `chore: some miscellaneous work`

The source of truth for these rules is [semantic-release/commit-analyzer](https://github.com/semantic-release/commit-analyzer). The `angular` preset is used by default, which is documented [here](https://github.com/conventional-changelog/conventional-changelog/tree/master/packages/conventional-changelog-angular).

[semantic-release]: https://github.com/semantic-release/semantic-release

## Examples

The [tests/examples](./tests/examples/) directory has example `dependencies.yaml` files along with their corresponding output files.

To create new `example` tests do the following:

- Create a new directory with a `dependencies.yaml` file in [tests/examples](tests/examples/)
- Ensure the `output` directories (e.g. `conda_dir`, `requirements_dir`, etc.) are set to write to `output/actual`
- Run `rapids-dependency-file-generator --config tests/examples/<new_folder_name>/dependencies.yaml` to generate the initial output files
- Manually inspect the generated files for correctness
- Copy the contents of `output/actual` to `output/expected`, so it will be committed to the repository and used as a baseline for future changes
- Add the new folder name to [test_examples.py](./tests/test_examples.py)
