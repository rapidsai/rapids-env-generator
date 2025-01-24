# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import datetime

from packaging.version import Version

import rapids_dependency_file_generator

DFG_VERSION = Version(rapids_dependency_file_generator.__version__)
project = "rapids-dependency-file-generator"
copyright = f"2022-{datetime.datetime.today().year}, NVIDIA Corporation"
author = "NVIDIA Corporation"
release = str(DFG_VERSION)

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "numpydoc",
]

templates_path = ["_templates"]
exclude_patterns: list[str] = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
html_theme_options = {
    "external_links": [],
    # https://github.com/pydata/pydata-sphinx-theme/issues/1220
    "icon_links": [],
    "github_url": "https://github.com/rapidsai/dependency-file-generator",
    "twitter_url": "https://twitter.com/rapidsai",
    "show_toc_level": 1,
    "navbar_align": "right",
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

autosummary_ignore_module_all = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
