from invoke import task

# TODO install the SendGrid API
#      https://github.com/sendgrid/sendgrid-python


@task
def make(ctx):
    # TODO Collect syllabi entries to generate email(s)
    raise NotImplementedError()


@task
def send(ctx):
    # TODO Send email to departments / list
    raise NotImplementedError()
