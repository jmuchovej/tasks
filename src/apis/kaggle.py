import json
import os
from hashlib import sha256
from typing import Tuple
from pathlib import Path

import requests
from invoke import task

from .. import j2env, read_from_disk
from ..concepts import Meeting


def _set_config_dir(ctx):
    config = Path(__file__).parent.parent / "templates" / "kaggle"
    os.environ["KAGGLE_CONFIG_DIR"] = str(config)
    ctx.run(f"chmod 600 {config / 'kaggle.json'}")


def _decrypt_key(ctx):
    """Decrypt `kaggle.json`; enables `ucfaibot` to interact with Kaggle.
    """
    pwd = os.getcwd()
    os.chdir(j2env.loader.package_path)

    # gpg: problem with agent: Inappropriate ioctl for device
    ctx.run(f"gpg --passphrase {ctx.kaggle.passwd} kaggle.json.gpg")
    ctx.run("chmod 600 kaggle.json")

    os.chdir(pwd)


def kernel_metadata(ctx, m: Meeting):
    """Generates `kernel-metadata.json` for each Kaggle competition.

    Currently, this can't utilize the Jinja2 template labeled: `kernel-metadata.json.j2`
    because JSON is really finnicky about single-/double-quotes. Ideally, Jinja2 would
    be able to do this, but until that day - the dict-based implementation is ideal.

    More info on the Kaggle API `kernel-metadata.json` file:
        https://github.com/Kaggle/kaggle-api/wiki/Kernel-Metadata
    """
    _username = ctx.settings.kaggle.username

    metadata_j2 = j2env.get_template("kaggle/kernel-metadata.json.j2")

    if type(m.kaggle) == bool:
        m.kaggle = {}

    use_competitions = not (
        "competitions" in m.kaggle and m.kaggle["competitions"] is False
    )

    for key in ["competitions", "datasets", "kernels"]:
        if key not in m.kaggle or type(m.kaggle[key]) == bool:
            m.kaggle[key] = []

    if "enable_gpu" not in m.kaggle:
        m.kaggle["enable_gpu"] = False

    if use_competitions:
        m.kaggle["competitions"].append(slug_competition(ctx, m))

    with open(ctx.path / str(m) / "kernel-metadata.json", "w") as f:
        kwargs = {
            "username": _username,
            "slug": slug_kernel(ctx, m),
            "kaggle": m.kaggle,
            "notebook": m.filename,
        }
        json.dump(json.loads(metadata_j2.render(**kwargs)), f, indent=2)


def _pull_kernel(ctx, m: Meeting):
    """Pull Kaggle Kernel in `kernel-metadata.json` to be diff'd.
    """
    _username = ctx.settings.kaggle.username
    _workbook = ctx.settings.suffixes.workbook

    existence_test = requests.get(
        f"https://kaggle.com/{_username}/{slug_kernel(ctx, m)}"
    )

    if existence_test.status_code != requests.codes.OK:
        return None
    else:
        kaggle_cmd = "kaggle k pull -p /tmp"
        ctx.run(f"{kaggle_cmd} {_username}/{slug_kernel(ctx, m)}")
        return Path("/tmp") / f"{slug_kernel(ctx, m)}{_workbook}"


def _diff_kernel(ctx, m: Meeting, remote: Path):
    """Uses `sha256` on local Workbook and Kaggle Kernel to determine if they differ.
    """
    _workbook = ctx.settings.suffixes.workbook
    local = ctx["path"] / str(m) / f"{m.filename}{_workbook}"

    remote_hash = sha256(open(remote, "rb").read()).hexdigest()
    local_hash = sha256(open(local, "rb").read()).hexdigest()

    return remote_hash != local_hash


def push_kernel(ctx, m: Meeting):
    """Pushes a Meeting's local Workbook to Kaggle Kernels.
    """
    _set_config_dir(ctx)
    path = _pull_kernel(ctx, m)
    diff = _diff_kernel(ctx, m, path) if path else True

    if diff:
        with ctx.cd(str(ctx.path / str(m))):
            ctx.run("kaggle k push")
    else:
        raise ValueError("Kernels are the same")


def create_competition(ctx):
    """TODO: Create a Meeting's associated Kaggle InClass Competition.
    """
    _set_config_dir(ctx)
    # NOTE this might be doable using https://github.com/puppeteer/puppeteer,
    #   Selenium will definitely work, though
    raise NotImplementedError()


def accept_competition(ctx):
    """TODO: Accept a Meeting's associated Kaggle InClass Competition rules.
    """
    _set_config_dir(ctx)
    # NOTE this might be doable using https://github.com/puppeteer/puppeteer,
    #   Selenium will definitely work, though
    raise NotImplementedError()


def slug_kernel(ctx, m: Meeting) -> str:
    """Generates Kaggle Kernel slugs of the form: `<group>-<semester>-<filename>`.
    e.g. If we consider the Spring 2020 "Building AI, the Human Way" lecture, the slug
    would be: `core-fa19-building-ai-the-human-way`.
    """
    return f"{ctx.group.name}-{ctx.group.semester}-{m.filename}"


def slug_competition(ctx, m: Meeting) -> str:
    """Kaggle InClass competitions are listed under general competitions. So, we take
    each meeting's `slug_kernel` and prepend `ORG_NAME` to that – so for AI@UCF, it we
    prepend `ucfai`.
    """
    return f"{ctx.settings.org_name}-{slug_kernel(ctx, m)}"
