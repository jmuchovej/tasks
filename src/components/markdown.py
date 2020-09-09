import re
from pathlib import Path

from invoke import Context

from . import website
from ..concepts import Meeting
from ..meeting import search


simple_instructions = """
<!-- TODO Add Meeting Notes/Contents here -->
<!-- NOTE Refer the Documentation if you're unsure how to format/add to this. -->
""".lstrip("\n")


def make_summaryfile(ctx: Context, query):
    m = search(ctx, query)

    ext = ctx.settings.suffixes.simplesummary
    path = ctx.path / str(m) / f"{m.filename}{ext}"
    if not path.exists():
        open(path, "w").write(simple_instructions)


def make_post(ctx: Context, query, **kwargs):
    m = search(ctx, query)

    ext = ctx.settings.suffixes.simplesummary
    path = ctx.path / str(m) / f"{m.filename}{ext}"

    md = open(path, "r").read()

    weight = kwargs.get("weight", -1)
    website.touch_meeting(ctx, m, body=md, weight=weight)
