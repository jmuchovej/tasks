"""Solutionbooks are the bread-and-butter of AI@UCF. These Notebooks are used
in all variety of tutorials and can be rendered as:
* Workbooks, to enable interactive tutorial/self-study sessions.
* Markdown Posts, to enable publication on the club website.

Currently, the following can be invoked:
* :meth:`.standardize`
* :meth:`.to_post`
* :meth:`.to_workbook`
"""
import pdb
import json

import nbformat as nbf
from jinja2 import Template
from nbconvert.exporters import MarkdownExporter, NotebookExporter
from nbconvert.preprocessors import TagRemovePreprocessor
from nbgrader.preprocessors import ClearOutput, ClearSolutions

from .. import j2env, read_from_disk
from ..meeting import search
from . import website


def make_solutionbook(ctx, query, **kwargs):
    """Ensures that all Solutionbooks have accurate headings, pathing, and metadata.
    """
    m = search(ctx, query)

    _solnbook = ctx.settings.suffixes.solutionbook

    standard = NotebookExporter()
    standard.register_preprocessor(
        TagRemovePreprocessor(remove_cell_tags=["template"]), enabled=True
    )

    setattr(m, "group", ctx.group)
    path = ctx.path / str(m) / f"{m.filename}{_solnbook}"
    # If the notebook doesn't exist, or it's empty
    if not path.exists() or path.stat().st_size == 0:
        nb = nbf.v4.new_notebook()
        nbf.write(nb, open(path, "w"))

    nb, _ = standard.from_filename(str(path))
    nb = nbf.reads(nb, as_version=4)

    # Inject Heading
    html_header = j2env.get_template("notebooks/header.html.j2")
    banner_url = Template(ctx.settings.hugo.banner_url).render(
        group=ctx.group, meeting=m
    )
    header = html_header.render(banner_url=banner_url, meeting=m)
    header_metadata = {"title": m.title, "tags": ["nb-title", "template"]}
    nb.cells.insert(0, nbf.v4.new_markdown_cell(header, metadata=header_metadata))

    # Inject data-loading cell
    from ..apis import kaggle

    py_dataset_path = j2env.get_template("notebooks/data-pathing.py.j2")
    dataset = py_dataset_path.render(slug=kaggle.slug_competition(ctx, m))
    dataset_metadata = {"language": "python", "tags": ["template"]}
    nb.cells.insert(1, nbf.v4.new_code_cell(dataset, metadata=dataset_metadata))

    # Inject Notebook Metadata
    nb_metadata = j2env.get_template("notebooks/nb-metadata.json.j2")
    metadata = nb_metadata.render(meeting=m)
    nb.metadata.update(json.loads(metadata))

    nbf.write(nb, open(path, "w"))


def make_workbook(ctx, query, **kwargs):
    """Generates a Workbook from a Solutionbook.

    Workbooks are stripped down Solutionbooks that, namely:
    - Have no output cells.
    - Replace `### BEGIN SOLUTION ... ### END SOLUTION` blocks with
      `raise NotImplementedError()` snippets for viewers to practice on.
    """
    m = search(ctx, query)

    workbook = NotebookExporter()

    workbook.register_preprocessor(ClearOutput(), enabled=True)
    workbook.register_preprocessor(ClearSolutions(enforce_metadata=False), enabled=True)
    # TODO migrate back to `enforce_metadata=True`

    # workbook.register_preprocessor(ValidateNBGrader(), enabled=True)
    # this is only useful if we can migrate back to `enforce_metadata=True`

    _workbook = ctx.settings.suffixes.workbook
    _solnbook = ctx.settings.suffixes.solutionbook

    try:
        path = ctx.path / str(m) / m.filename

        nb, _ = workbook.from_filename(str(path.with_suffix(_solnbook)))
        nb = nbf.reads(nb, as_version=4)

        nbf.write(nb, open(path.with_suffix(_workbook), "w"))
    except Exception:
        raise Exception(f"Workbook export failed on `{m}`.")


def make_post(ctx, query, **kwargs):
    """Preprocess a Solutionbook and prepare it to post on https://ucfai.org/.
    """
    m = search(ctx, query)

    _solnbook = ctx.settings.suffixes.solutionbook

    as_post = MarkdownExporter()
    as_post.extra_loaders = [j2env.loader]
    as_post.template_file = f"notebooks/to-post.md.j2"
    as_post.no_prompt = True
    as_post.register_preprocessor(
        TagRemovePreprocessor(remove_cell_tags=["nb-title"], enabled=True)
    )

    name = ctx.path / f"{m}/{m.filename}{_solnbook}"
    # Default to `git`-based "Last modified..."
    # lastmod = pd.Timestamp(name.stat().st_mtime, unit="s")
    # setattr(m, "lastmod", lastmod)

    nb, _ = as_post.from_filename(str(name))

    weight = kwargs.get("weight", -1)
    try:
        website.touch_meeting(ctx, m, body=nb, weight=weight)
    except:
        raise
        pdb.set_trace()
