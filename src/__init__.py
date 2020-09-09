import json
from pathlib import Path

from invoke import task
from ruamel.yaml import YAML
from pandas import Timestamp
from jinja2 import Environment, PackageLoader

from .concepts import Group, Meeting


yaml = YAML()

yaml.register_class(Group)
yaml.register_class(Meeting)


def _repr_timestamp(representer, data):
    return representer.represent_scalar("!Timestamp", str(data))


def _init_timestamp(loader, data):
    data = loader.construct_scalar(data)
    return Timestamp(data)


yaml.representer.add_representer(type(Timestamp(None)), _repr_timestamp)
yaml.representer.add_representer(Timestamp, _repr_timestamp)
yaml.constructor.add_constructor("!Timestamp", _init_timestamp)

j2env = Environment(loader=PackageLoader("tasks", "src/templates"),)
j2env.filters["jsonify"] = json.dumps


def read_from_disk(ctx, group="", semester=""):
    config = yaml.load(open(Path(__file__).parent.parent / "config.yml", "r"))
    ctx["settings"] = config

    # Prefer values set in Context over arguments
    if not group and hasattr(ctx, "group") and ctx.group:
        group = ctx.group

    if not semester and hasattr(ctx, "semester") and ctx.semester:
        semester = ctx.semester

    try:
        if not isinstance(group, Group):
            group = yaml.load(open(Path(group) / semester / "group.yml", "r"))
    except FileNotFoundError:
        if not semester:
            from .tools import cal

            group = cal.get_next_semester(ctx, group)
        else:
            defaults = ctx.settings.defaults[group]
            group = Group(
                required={
                    "name": group,
                    "semester": semester,
                    "frequency": defaults.frequency,
                    "use-notebooks": defaults.needs_notebooks,
                }
            )
    finally:
        group = group.flatten()
        ctx["group"] = group
        ctx["semester"] = group.semester

    try:
        syllabus = yaml.load(open(group.asdir() / "syllabus.yml", "r"))
    except FileNotFoundError:
        syllabus = []
    finally:
        ctx["syllabus"] = syllabus

    ctx["path"] = group.asdir()

    return ctx


def read_and_flatten(ctx, **kwargs):
    ctx = read_from_disk(ctx, **kwargs)
    ctx.syllabus = [m.flatten() for m in ctx.syllabus]

    return ctx


__all__ = [
    "group",
    "meeting",
]
