from typing import Union


def _print(msg, prefix: Union[bool, str] = "1. "):
    import emoji

    fn = emoji.emojize

    # import emojis
    # fn = emojis.encode
    if prefix:
        print(prefix, end="")
    print(fn(msg.strip(), use_aliases=True))


def begin(msg, prefix="## "):
    _print(msg, prefix)


def success(s: str = "", prefix: str = "1. "):
    _print(f":white_check_mark: {s}", prefix)


def fail(s: str = "", prefix: str = "1. "):
    _print(f":x: {s}", prefix)


def warn(s: str = "", prefix: str = "1. "):
    _print(f":rotating_light: {s}", prefix)


def test(assertion, msg, halt: bool = True):
    try:
        assert assertion
    except AssertionError:
        fail(msg)
        if halt:
            exit(-1)
