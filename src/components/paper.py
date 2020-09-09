import requests
from invoke import task

from ..concepts import Meeting
from ..tools import status


def download(ctx, m: Meeting):
    """Downloads papers and names them based on keys for meetings.
    """

    folder = ctx.path / str(m)

    for title, link in m.papers.items():
        prefix = "  1. "
        try:
            with open(folder / f"{title}.pdf", "wb") as pdf:
                pdf.write(requests.get(link).content)
            # TODO Check for corruptness / PDF headers
            status.success(f"Successfully downloaded `{title}`.", prefix=prefix)
        except ConnectionError:
            status.fail(f"Unable to access link for `{title}`.", prefix=prefix)
