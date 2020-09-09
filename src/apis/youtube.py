from invoke import task


@task
def upload_video(ctx):
    # Honestly not too sure this would be useful to have, as renders need to be local
    raise NotImplementedError()


@task
def make_playlist(ctx):
    # TODO use YouTube API Key to create playlists for a given semester
    raise NotImplementedError()
