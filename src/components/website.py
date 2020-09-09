import pdb

from invoke import Context


from ..concepts import Meeting
from ..apis import hugo

def load_config(key: str = ""):
    return hugo.load_data("config.yml", key=key)


def cleanup_authors(ctx):
    pass


def touch_author(ctx, author):
    hugo.touch_author(ctx, author)


def touch_group(ctx):
    hugo.touch_group(ctx)


def touch_semester(ctx):
    hugo.touch_semester(ctx)


def touch_meeting(ctx: Context, m: Meeting, body: str, weight: int = -1, **kwargs):
    editor = hugo.touch_post(ctx, m)

    editor.fm["title"] = m.title
    editor.fm["linktitle"] = m.title

    editor.fm["date"] = m.date.isoformat()
    # ctx.settings.hugo ordering prefers 1-based indexing
    if weight > -1:
        editor.fm["weight"] = weight + 1

    editor.fm["authors"] = m.authors

    from ..tools import urls

    editor.fm["urls"]["youtube"] = urls.youtube(ctx, m)
    editor.fm["urls"]["slides"] = urls.slides(ctx, m)
    editor.fm["urls"]["github"] = urls.github(ctx, m)
    editor.fm["urls"]["kaggle"] = urls.kaggle(ctx, m)
    editor.fm["urls"]["colab"] = urls.colab(ctx, m)

    editor.fm["location"] = m.room
    # editor.fm["cover"] = m.cover_image

    editor.fm["tags"] = m.tags
    editor.fm["abstract"] = m.abstract

    try:

        def makeurl(download_name):
            """This generates a URL like...
            https://github.com/{org_name}/{repo}/raw/{branch}/{semester}/{pdf}
            """
            return "/".join(
                [
                    ctx.settings["version-control"].repo_owner,
                    ctx.group.name,
                    "raw",
                    "master",
                    ctx.group.semester,
                    f"{download_name}.pdf",
                ]
            )

        m.papers = {k: makeurl(k) for k in m.papers.keys()}
        editor.fm["papers"] = m.papers
    except (AttributeError):
        pass

    try:
        editor.content = ["\n", body]
    except NameError:
        pass

    editor.dump()
