import shutil
from pathlib import Path

from invoke import task
import pandas as pd

from . import yaml, j2env, read_from_disk, read_and_flatten
from .concepts import Group, Meeting
from .tools import status, cal
from .components import website


@task
def new_group(ctx, group):
    # TODO check that `group` does not exist on system
    # TODO create git repository and set `origin`
    # TODO copy workflows necessary to get a semester up-and-running
    raise NotImplementedError()


@task
def add_semester(ctx, group="", semester=""):
    if "semester" in ctx:
        del ctx["semester"]

    ctx = read_from_disk(ctx, group, semester)
    print(f"# Adding `{ctx.group.semester}` to `{ctx.group.name.capitalize()}`")

    ctx.path.mkdir()

    # region Generate Group defintion & prepare `invoke.yml`
    status.begin("Generate Group Definitions & Write `invoke.yml`")
    inv = j2env.get_template("group/invoke.yml.j2")
    inv = inv.render(group=ctx.group.name, semester=ctx.group.semester)
    inv = yaml.load(inv)

    schedule = cal.temp_schedule(ctx.group)
    ctx.group.startdate = schedule[0]

    files_to_write = {
        # Write Group metadata to file
        ctx.path / "group.yml": ctx.group,
        # Write Context to file (e.g. group-name and semester)
        ctx.path / "invoke.yml": inv,
        ctx.path.parent / "invoke.yml": inv,
    }

    for filepath, contents in files_to_write.items():
        yaml.dump(contents, open(filepath, "w"))
        status.success(f"Wrote `{filepath}`.")
    # endregion

    # region Create `Meetings` and dump them to YAML
    status.begin("Create Dummy Meetings")
    meetings = [
        Meeting.placeholder(
            ctx=ctx,
            m=f"meeting{idx:02d}",
            date=date,
            required={"needs-notebooks": ctx.group.optional.get("use-notebooks", False)}
        )
        for idx, date in enumerate(schedule)
    ]
    status.success(f"Created `{ctx.path / 'syllabus.yml'}`.")
    yaml.dump(meetings, ctx.path / "syllabus.yml")
    # endregion

    exit(0)  # Enforce a prompt exit


@task
def validate_syllabus(ctx, group="", semester=""):
    """Reads necessary configuration files to act over a semester."""
    ctx = read_from_disk(ctx, group, semester)
    print(f"# Validating Syllabus for `{ctx.group.name.capitalize()}`")

    # TODO validate dates follow the meeting pattern and ping Discord if not

    status.test(
        ctx.group.startdate, "Group needs `startdate` to proceed with generation."
    )

    ls = [x for x in ctx.path.iterdir() if x.is_dir()]
    empty = (len(ls) == 0)

    # region Set defaults if no value is set
    if empty:
        status.begin("Setting Defaults for New Semester")
        for idx, m in enumerate(ctx.syllabus):
            status.begin(str(m), prefix="### ")
            # Set meeting dates based on the frequency
            # TODO check that meetings aren't during holidays
            delta = pd.Timedelta(days=7 * idx * ctx.group.required["frequency"])
            m.required["date"] = ctx.group.required["startdate"] + delta
            status.success(f"Set default date: {m.required['date']}.")

            if not m.required["room"]:
                m.required["room"] = ctx.group.room
                status.success(f"Set default room: {m.required['room']}.")

    status.success("Successfully set defaults in `syllabus.yml`.", prefix="")
    yaml.dump(ctx.syllabus, ctx.path / "syllabus.yml")
    # endregion

    status.begin(f"Check Authorship for `{ctx.group.name.capitalize()}` Meetings")
    for idx, m in enumerate(ctx.syllabus):
        authors = ctx.group.authors()
        missing = set(map(str.lower, m.required["authors"])) - authors
        if m.required["authors"] and len(missing) > 0:
            status.warn(
                f"`{m.required['title']}`: Could not find `{missing}` in Group's "
                f"authors. Please add them."
            )
        elif not m.required["authors"]:
            status.warn(f"`{m.required['title']}` has no authors. Please add them.")
        elif not authors:
            status.warn(f"Group has no authors. Please add them.")
    # endregion

    # region Sort Syllabus by date
    status.begin(f"Sorting `{ctx.group.semester}` semester by date.")

    n_uniq = len({x.required["date"] for x in ctx.syllabus})
    n_base = len(ctx.syllabus)
    status.test(
        (n_uniq == n_base),
        """Collision found.
        Meetings must have unique dates. Recheck `syllabus.yml`.
        """,
    )

    sorted_syllabus = sorted(ctx.syllabus, key=lambda x: x.required["date"])
    yaml.dump(sorted_syllabus, ctx.path / "syllabus.yml")
    status.success("Re-ordered syllabus.")
    # endregion


@task
def touch(ctx, group="", semester=""):
    """Mimics Unix `touch` and creates/updates a Semester for a Group."""
    ctx = read_and_flatten(ctx, group=group, semester=semester)
    print(f"# Touching `{ctx.group.name.capitalize()}`")

    # region Create / Rename Folders
    status.begin("Touch Meeting Directories")
    syllabus = {m.id: ctx.path / str(m) for m in ctx.syllabus}
    ondisk = sorted([x for x in ctx.path.glob("??-??-*/") if x.is_dir()])
    ondisk = {open(p / ".metadata", "r").read(): p for p in ondisk}

    created = 0
    for sha, meeting in syllabus.items():
        try:
            ondisk[sha].rename(meeting)
        except (FileNotFoundError, KeyError):
            meeting.mkdir()
            open(meeting / ".metadata", "w").write(sha)
            created += 1
            ondisk[sha] = meeting

    mode = "Created" if created / len(syllabus) > 0.5 else "Updated"
    status.success(f"{mode} Meeting directories.")
    # endregion

    # region Rename matching folder contents
    status.begin("Match Necessary Contents to Directory Name")
    for sha, meeting in syllabus.items():
        prv_name = ondisk[sha].stem[6:]  # only look at filenames
        new_name = meeting.stem[6:]  # only look at filenames

        for child in meeting.iterdir():
            if child.stem.startswith(prv_name):
                ext = "".join(child.suffixes)
                child.rename(child.parent / f"{new_name}{ext}")
    # endregion

    # region Update authorship on the website
    status.begin(f"Touch `{ctx.group.semester}` Semester in `{ctx.settings.website.url}`")
    website.touch_semester(ctx)

    # endregion
    # region Update authorship on the website
    status.begin(f"Touch Authors Contributing to `{ctx.group.name.capitalize()}`")

    for author in ctx.group.authors():
        try:
            website.touch_author(ctx, author.lower())
            status.success(f"Updated `{author.lower()}`.")
        except:
            status.fail(f"Failed to update `{author.lower()}`.")
            raise
    # endregion


@task
def cleanup(ctx, group="", semester=""):
    """Keeps the Group tidy with proper naming and the like."""
    ctx = read_and_flatten(ctx, group=group, semester=semester)
    print(f"# Cleaning up `{ctx.group.name.capitalize()}`")

    # region Cleanup dangling Meeting directories
    status.begin("Clean-up Dangling Meeting Directories")
    syllabus = {m.id: ctx.path / str(m) for m in ctx.syllabus}

    ondisk = sorted([x for x in ctx.path.glob("??-??-*/") if x.is_dir()])
    ondisk = {open(p / ".metadata", "r").read(): p for p in ondisk}

    ondisk_and_syllabus = set(ondisk.keys()).intersection(set(syllabus.keys()))

    for sha, folder in ondisk.items():
        if sha not in ondisk_and_syllabus:
            shutil.rmtree(folder)
    # region

    # TODO Cleanup Coordinators on the website (mostly their roles)
    status.begin("Clean-up Changes in Coordinators")

    # TODO Cleanup dangling Meeting pages
    status.begin("Clean-up Dangling Meeting Pages")
