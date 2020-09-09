import re

import requests


def youtube(ctx, m):
    """Normalizes YouTube URLs."""
    # YouTube URLs take the following form:
    #   https://www.youtube.com/watch?v=dQw4w9WgXcQ
    #   https://youtu.be/dQw4w9WgXcQ

    try:
        url = m.optional["urls"]["youtube"]
    except (TypeError, KeyError, AttributeError):
        return ""

    #   YouTube IDs are likely to stay 11-characters, but we'll see:
    #   https://stackoverflow.com/a/6250619
    if url and len(url) > 11 and "youtu" in url:
        # remove the protocol, www, and YouTube's domain name
        proto = "(?:https?://)?"
        ln_old = "(?:www\.)?youtube.com/watch?v="
        ln_new = "youtu.be"
        yt_full = f"{proto}(?:{ln_old}|{ln_new})"

        # "...|$" returns the empty string if not a match
        url = re.sub(f"{yt_full}|$", "", url)
        url = re.search("([A-Za-z0-9-_]{11})", url).group(0)
        url = f"https://youtu.be/{url}"
        if requests.get(url).status_code == requests.codes.OK:
            return url

    return ""


def slides(ctx, m):
    """Normalizes GSlides URLs."""

    try:
        url = m.optional["urls"]["slides"]
    except (TypeError, KeyError, AttributeError):
        return ""

    if url and "docs" in url and "presentation" in url:
        # Google Slides URLs take the following form:
        #   https://docs.google.com/presentation/d/14uUXIrdmXMGChj4dYaCZxcQ-rFonLmKqlSppLu8cY_I
        # remove the protocol, www, and Google Docs' domain name
        docs_base_url = "(?:https?://)?docs.google.com/presentation/d/"

        # "...|$" returns the empty string if not a match
        url = re.sub(f"{docs_base_url}|$", "", url)
        url = url.split("/", maxsplit=1)[0]

    url = f"https://docs.google.com/presentation/d/{url}"

    if requests.get(url).status_code == requests.codes.OK:
        return url

    # TODO based on how using `slides` in Hugo Academic works out, update this

    return ""


def github(ctx, m):
    """Generates GitHub URLs directly to the meeting notes."""
    # Our GitHub URLs take the form:
    #   https://github.com/ucfai/<meeting.group>/blob/master/<meeting.group.semester>/<meeting>
    #   e.g. https://github.com/ucfai/core/fa19/blob/master/2019-09-18-regression

    url = "/".join(
        [
            ctx.settings["version-control"].repo_owner,
            ctx.group.name,
            "blob",
            "master",
            ctx.group.semester,
            repr(m),
            f"{m.filename}{ctx.settings.suffixes.workbook}",
        ]
    )
    return url if requests.get(url).status_code == requests.codes.OK else ""


def kaggle(ctx, m):
    """Generates the Kaggle URL for Kernels to be published on the website."""
    from ..apis.kaggle import slug_kernel

    _username = ctx.settings.kaggle.username
    url = f"https://kaggle.com/{_username}/{slug_kernel(ctx, m)}"
    return url if requests.get(url).status_code == requests.codes.OK else ""


def colab(ctx, m):
    """Generates the a Google Colab URL from the GitHub URL."""
    url = github(ctx, m)

    if url and requests.get(url).status_code == requests.codes.OK:
        return url.replace(
            ctx.settings["version-control"].platform,
            "https://colab.research.google.com/github",
        )
    else:
        return ""
