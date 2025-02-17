# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import toml
import os
import sys

sys.path.insert(0, os.path.abspath('../'))
pyproject = toml.load('../pyproject.toml')

project = 'ProxyProviders'
copyright = '2025, David Teather'
author = 'David Teather'
release = pyproject['project']['version']

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx.ext.githubpages",
    "sphinx.ext.napoleon",
    "myst_parser",
]

autosummary_generate = True

autodoc_default_flags = ['members', 'undoc-members', 'show-inheritance']
autodoc_member_order = 'bysource'

templates_path = ["_templates"]
exclude_patterns = ["docs", "Thumbs.db", ".DS_Store"]

napoleon_google_docstring = True



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']
html_baseurl = "https://davidteather.github.io/proxyproviders/"

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
source_suffix = {".rst": "restructuredtext", ".md": "markdown", ".txt": "rst"}