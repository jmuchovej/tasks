from pathlib import Path
import textwrap
from typing import Dict
from hashlib import sha256

import pandas as pd
from invoke import Context
from ruamel.yaml.comments import CommentedSeq, CommentedMap
from ruamel.yaml.representer import FoldedScalarString


def _inline_list(*ls):
    ls = CommentedSeq(*ls)
    ls.fa.set_flow_style()
    return ls


def _multiline_str(s, width=82):  # width=82 because 88-6 (6=indent level)
    return FoldedScalarString("".join(textwrap.wrap(s, width=width)))


class Meeting:
    def __init__(self, required: Dict, optional: Dict = {}):
        self.required = CommentedMap()
        self.required["id"] = required["id"]
        self.required["date"] = pd.Timestamp(required.get("date", ""))
        self.required["title"] = required["title"]
        self.required["authors"] = _inline_list(required.get("authors", []))
        self.required["filename"] = required["filename"]
        self.required["cover-image"] = required.get("cover-image", "")
        self.required["tags"] = _inline_list(required.get("tags", []))
        self.required["room"] = required.get("room", "")
        self.required["abstract"] = _multiline_str(  # Need value for ">" to play nicely
            required.get("abstract", "We're filling this out!")
        )

        self.optional = CommentedMap()
        self.optional.yaml_add_eol_comment(
            "All `optional` keys are enumerated in the Documentation"
        )

        if "use-notebooks" in optional:
            self.optional["use-notebooks"] = optional["use-notebooks"]

        if "urls" in optional:
            self.optional["urls"] = optional["urls"]
            if self.optional["urls"]:
                self.optional["urls"]["slides"] = optional["urls"].get("slides", "")
                self.optional["urls"]["youtube"] = optional["urls"].get("youtube", "")

        if "kaggle" in optional:
            self.optional["kaggle"] = optional["kaggle"]
            if self.optional["kaggle"] is not True:
                if self.optional["kaggle"].get("kernels", False):
                    self.optional["kaggle"]["kernels"] = _inline_list(
                        optional["kaggle"]["kernels"]
                    )

                if self.optional["kaggle"].get("datasets", False):
                    self.optional["kaggle"]["datasets"] = _inline_list(
                        optional["kaggle"]["datasets"]
                    )

                if self.optional["kaggle"].get("enable_gpu", False):
                    self.optional["kaggle"]["enable_gpu"] = optional["kaggle"]["enable_gpu"]

                if self.optional["kaggle"].get("competitions", False):
                    self.optional["kaggle"]["competitions"] = _inline_list(
                        optional["kaggle"]["competitions"]
                    )

        if "papers" in optional:
            self.optional["papers"] = optional["papers"]

    def __str__(self):
        return repr(self)

    def __repr__(self):
        s = self.required["filename"]

        if not pd.isnull(self.required["date"]):
            return f"{self.required['date'].isoformat()[5:10]}-{s}"

        return s

    def flatten(self):
        try:
            if self.flattened:
                raise ValueError("Already flattened.")
        except AttributeError:
            if self.optional:
                self.__dict__.update(self.optional)

            if self.required:
                self.__dict__.update(self.required)

            self.date = pd.Timestamp(self.date)
            self.flattened = True
        finally:
            return self

    def setup_or_rename(self, parent: Path = Path(".")):
        path = parent / repr(self)

        path.mkdir()

        with open(path / ".metadata", "w") as f:
            f.write(self.id)

    @staticmethod
    def placeholder(ctx: Context, m: str, date: pd.Timestamp, **kwargs):
        required = dict(
            id=sha256(m.encode("utf-8")).hexdigest(),
            title=m,
            date=date.isoformat(),
            filename=m,
        )
        required.update(kwargs.get("required", {}))
        optional = kwargs.get("optional", {})

        return Meeting(required, optional)
