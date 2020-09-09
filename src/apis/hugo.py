import re
import os
from pathlib import Path
from typing import Tuple
from functools import cmp_to_key

from invoke import task
import docker
from jinja2 import Template

from .. import read_from_disk
from ..concepts import Coordinator, Group, Meeting
from ..tools import EditableFM, status, urls, sort
from ..meeting import search


command = Template("hugo new --kind {{ kind }} {{ path }}")

direc_group = Template("{{ ctx.group.semester }}-{{ ctx.group.name }}-director")
direc = Template("{{ ctx.group.semester }}-director")

coord_group = Template("{{ ctx.group.semester }}-{{ ctx.group.name }}-coordinator")
coord = Template("{{ ctx.group.semester }}-coordinator")

guest_group = Template("{{ ctx.group.semester }}-{{ ctx.group.name }}-guest")
guest = Template("{{ ctx.group.semester }}-guest")

advis_group = Template("{{ ctx.group.semester }}-{{ ctx.group.name }}-advisor")
advis = Template("{{ ctx.group.semester }}-advisor")


templates = {
    "direc": (direc_group, direc),
    "coord": (coord_group, coord),
    "guest": (guest_group, guest),
    "advis": (advis_group, advis),
}

_hugo_path = Path()


def hugo_via_container(ctx, name: str = "hugo"):
    if os.environ.get("GITHUB_ACTIONS", False):
        site_src = f"/{ctx.settings.hugo.repo}"
    else:
        site_src = f"{os.getcwd()}/{ctx.settings.hugo.repo}"

    global _hugo_path
    _hugo_path = Path(site_src)

    client = docker.from_env()

    try:
        container = client.containers.get(name)
        container.unpause()
    except docker.errors.NotFound:
        container = client.containers.create(
            image=ctx.settings.hugo.image,
            auto_remove=False,
            detach=False,
            environment={"HUGO_THEME": "academic", "HUGO_WATCH": "true",},
            volumes={f"{site_src}": {"bind": "/src", "mode": "rw",},},
            working_dir="/src",
            name=name,
        ) 
        container.start()

    return container, site_src


def touch_group(ctx):
    """Creates a new .ctx.group.
    Adds a `_index.md` page to create a new .Group landing page.

    :params ctx: Invoke Context that should contain: .Group

    :returns: None
    """
    container, _ = hugo_via_container(ctx)
    group_path = f"groups{ctx.group.name}"
    new_author = command.render(kind="semester", path=group_path,)

    res = container.exec_run(new_author)
    output = res.output.decode("utf-8")

    # editor = EditableFM(f"{site_src}/content/{group_path}")
    # editor.load("_index.md")

    # NOTE Any programmatic edits to the Group should be made here

    # editor.dump()


def touch_semester(ctx):
    """Creates a new semester for a given .ctx.group.
    Adds a new `_index.md` page for display on the .Group landing page.

    :params ctx: Invoke Context that should contain: .Group

    :returns: None
    """
    container, site_src = hugo_via_container(ctx)
    # import pdb; pdb.set_trace()
    group_path = f"groups/{repr(ctx.group)}"
    new_semester = command.render(kind="semester", path=group_path,)

    expanded_path = f"{site_src}/content/{group_path}"
    Path(expanded_path).mkdir(exist_ok=True)

    res = container.exec_run(new_semester)
    output = res.output.decode("utf-8")

    if "create" in output:
        status.success(f"Created `{ctx.path}/_index.md`.")

    editor = EditableFM(expanded_path)
    editor.load("_index.md")

    editor.fm["date"] = str(ctx.group.startdate)
    editor.fm["frequency"] = ctx.group.frequency
    editor.fm["location"] = ctx.group.room

    editor.dump()

    container.pause()


def touch_author(ctx, author=""):
    """Creates an author page everyone that contributes to a semester's content.

    :params ctx: Invoke Context that should contain: .Group

    :returns: None
    """
    container, site_src = hugo_via_container(ctx)

    author_path = f"authors/{author}/"
    new_author = command.render(kind="author", path=author_path,)

    res = container.exec_run(new_author)
    output = res.output.decode("utf-8")

    editor = EditableFM(f"{site_src}/content/{author_path}")
    editor.load("_index.md")

    teams = set(editor.fm["ucfai"]["teams"] + [ctx.group.semester])
    editor.fm["ucfai"]["teams"] = sorted(list(teams), key=sort.semester, reverse=True)

    if author in map(str.lower, ctx.group.directors):
        groups = [x.render(ctx=ctx) for x in templates["direc"]] + ["Director", ]
    elif author in map(str.lower, ctx.group.coordinators):
        groups = [x.render(ctx=ctx) for x in templates["coord"]] + ["Coordinator", ]
    elif author in map(str.lower, ctx.group.guests):
        groups = [x.render(ctx=ctx) for x in templates["guest"]] + ["Guest", ]
    elif author in map(str.lower, ctx.group.advisors):
        groups = [x.render(ctx=ctx) for x in templates["advis"]] + ["Advisor", ]
    else:
        groups = []

    try:
        roles = [groups[-1]]
    except IndexError:
        roles = []

    # region Semi-Complex Group filtering/sorting
    groups = set(editor.fm["user_groups"] + groups)

    non_sem = filter(lambda x: not re.match("(fa|sp|su)\d{2}", x), groups)
    isa_sem = filter(lambda x: bool(re.match("(fa|sp|su)\d{2}", x)), groups)

    groups = sorted(list(non_sem))
    groups += sorted(list(isa_sem), key=sort.roles, reverse=True)

    editor.fm["user_groups"] = groups
    # endregion

    roles = set(editor.fm["ucfai"]["roles"] + roles)
    editor.fm["ucfai"]["roles"] = sorted(list(roles))

    editor.dump()

    container.pause()


def cleanup_authors(ctx):
    """Ensure author activity on site matches repository activity.

    :params ctx: Invoke Context that should contain: .Group

    :returns: None
    """
    container, site_src = hugo_via_container(ctx)
    authors = Path(f"{site_src}/content/authors")

    group = ctx["group"]
    _templates = [x.render(group=group) for x in templates]

    for author in authors.iterdir():
        editor = EditableFM(author)
        editor.load("_index.md")

        if author.stem not in ctx.group.authors():
            for template in _templates:
                try:
                    index = editor.fm["user_groups"].index(template)
                    del editor.fm["user_groups"][index]
                except ValueError:
                    pass

            try:
                index = editor.fm["ucfai"]["teams"].index(ctx.group.semester)
                del editor.fm["ucfai"]["teams"][index]
            except ValueError:
                pass

        editor.dump()
    status.success("Cleaned up roles.")

    container.pause()


def touch_post(ctx, m, weight=-1, **kwargs):
    """Renders Jupyter Notebook to ctx.settings["hugo"]-ready Markdown.

    :params ctx: Invoke Context that should contain: [.Group, .Syllabus]

    :returns: None
    """
    container, site_src = hugo_via_container(ctx)

    meeting_path = f"groups/{ctx.group.name}/{ctx.group.semester}"
    meeting_file = f"{m.filename}.md"
    new_meeting_post = command.render(
        kind="group-meeting", path=f"{meeting_path}/{meeting_file}"
    )
    res = container.exec_run(new_meeting_post)
    output = res.output.decode("utf-8")

    editor = EditableFM(f"{site_src}/content/{meeting_path}")
    editor.load(meeting_file)

    container.pause()

    return editor


def load_data(path, key):
    from .. import yaml
    if "yml" not in path:
        path += ".yml"

    global _hugo_path

    data = yaml.load(_hugo_path / "data" / path)

    try:
        return data[key]
    except KeyError:
        return data
