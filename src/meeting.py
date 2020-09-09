import re
import json

from invoke import Context, task
import nbformat as nbf
from jinja2 import Template
from nbconvert.exporters import MarkdownExporter, NotebookExporter
from nbconvert.preprocessors import TagRemovePreprocessor
from nbgrader.preprocessors import ClearOutput, ClearSolutions

from . import j2env, read_and_flatten
from .concepts import Meeting
from .apis import kaggle
from .tools import status


def _has(ctx, m: Meeting, attribute):
    # import pdb; pdb.set_trace()
    if attribute in m.required:
        return bool(m.required[attribute])
    elif m.optional and attribute in m.optional:
        return bool(m.optional[attribute])
    elif attribute in ctx.group.required:
        return bool(ctx.group.required[attribute])
    elif ctx.group.optional and attribute in ctx.group.optional:
        return bool(ctx.group.optional[attribute])

    return False


@task
def touch(ctx, group="", semester="", query=""):
    """Mimics Unix `touch` and creates/updates Meetings."""
    from .components import notebook, markdown, paper

    ctx = read_and_flatten(ctx, group=group, semester=semester)
    print(f"# Touching `{ctx.group.name.capitalize()}` Meetings")

    # TODO Creates / renames meeting directories (and known contents)
    if query:
        meetings = [search(ctx, query)]
    else:
        meetings = ctx.syllabus

    for meeting in meetings:
        print(f"## {meeting.title}")

        # Create SolutionBook is there's a need for it, otherwise create a SummaryFile
        if _has(ctx, meeting, "use-notebooks"):
            try:
                notebook.make_solutionbook(ctx, meeting)
                status.success("Successfully created SolutionBook.")
            except Exception:
                status.fail("Failed to create SolutionBook.")
                raise

            try:
                if _has(ctx, meeting, "kaggle"):
                    kaggle.kernel_metadata(ctx, meeting)
                    status.success("Created `kernel-metadata.json`.")
            except Exception:
                status.fail("Failed to create `kernel-metadata.json`.")
                raise
        else:
            try:
                markdown.make_summaryfile(ctx, meeting)
                status.success("Successfully created SummaryFile.")
            except Exception:
                status.fail("Failed to make SummaryFile.")
                raise

        # TODO Downloads papers
        if _has(ctx, meeting, "papers"):
            paper.download(ctx, meeting)


@task
def publish(ctx, group="", semester="", query=""):
    """Prepares "camera-ready" versions of Meeting contents for public use."""
    ctx = read_and_flatten(ctx, group=group, semester=semester)
    print(f"# Publishing `{ctx.group.name.capitalize()}` Meetings")

    from .components import notebook, markdown

    ctx = read_and_flatten(ctx, group=group, semester=semester)

    # TODO Creates / renames meeting directories (and known contents)
    weight = 0
    if query:
        meetings = [search(ctx, query)]
        weight = -1
    else:
        meetings = ctx.syllabus

    for meeting in meetings:
        print(f"## {meeting.title}")
        if re.match("meeting\d\d", meeting.filename):
            status.fail("Template filename. Please rename.")
            continue

        if _has(ctx, meeting, "use-notebooks"):
            try:
                notebook.make_workbook(ctx, meeting)
                status.success("Successfully exported SolutionBook to WorkBook.")
            except Exception:
                status.fail("Failed to export SolutionBook to WorkBook.")
                raise

            try:
                # import pdb; pdb.set_trace()
                notebook.make_post(ctx, meeting, weight=weight)
                status.success("Successfully exported SolutionBook to post.")
            except Exception:
                status.fail("Failed to export SolutionBook to post.")
                raise

            try:
                if _has(ctx, meeting, "kaggle"):
                    kaggle.push_kernel(ctx, meeting)
                    status.success("Successfully pushed WorkBook to Kaggle.")
            except Exception:
                status.fail("Failed to push WorkBook to Kaggle.")
                raise

            # if _has(ctx, meeting, "kaggle"):
            #     # TODO Creates `kernel-metadata.json` for Kaggle
            #     kaggle.push_kernel(ctx, meeting)
        else:
            try:
                markdown.make_post(ctx, meeting, weight=weight)
                status.success("Successfully exported SummaryFile to post.")
            except Exception:
                status.fail("Failed to export SummaryFile to post.")
                raise

        weight += 1


def search(ctx, query):
    if type(query) == Meeting:
        m = query
    elif type(query) == str:
        bytitle = filter(lambda x: query.lower() in x.filename.lower(), ctx.syllabus)
        m = list(bytitle)[0]
    else:
        raise ValueError("`query` must be a string or Meeting.")

    return m
