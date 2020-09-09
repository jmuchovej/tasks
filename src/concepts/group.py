from typing import Dict, List
import textwrap
from pathlib import Path
import os

import pandas as pd
from ruamel.yaml.comments import CommentedSeq, CommentedMap
from ruamel.yaml.representer import FoldedScalarString


long2short = {"fall": "fa", "summer": "su", "spring": "sp"}
# invert `long2short`
short2long = {k: v for v, k in long2short.items()}

def _inline_list(*ls):
    ls = CommentedSeq(*ls)
    ls.fa.set_flow_style()
    return ls


def _multiline_str(s, width=82):  # width=82 because 88-6 (6=indent level)
    return FoldedScalarString("".join(textwrap.wrap(s, width=width)))


# TODO convert Syllabus into a YAML-ready dumper
class Group:
    def __init__(self, required: Dict, optional: Dict = {}):
        self.required = CommentedMap()
        self.required["name"] = required["name"]
        self.required["room"] = required.get("room", "")

        self.required["semester"] = required["semester"]
        self.required["startdate"] = pd.Timestamp(required.get("startdate", None))
        self.required["frequency"] = required["frequency"]

        # eligible authors
        self.required["directors"] = _inline_list(required.get("directors", []))
        self.required["coordinators"] = _inline_list(required.get("coordinators", []))
        self.required["guests"] = _inline_list(required.get("guests", []))
        self.required["advisors"] = _inline_list(required.get("advisors", []))

        self.required["summary"] = _multiline_str(required.get("summary", ""))

        self.optional = CommentedMap()
        self.optional.yaml_add_eol_comment("All `optional` keys are enumerated in the Documentation")
        # semester options
        if "use-kaggle" in optional:
            self.optional["use-kaggle"] = optional["use-kaggle"]
        if "use-notebooks" in optional:
            self.optional["use-notebooks"] = optional["use-notebooks"]
        if "pull-papers" in optional:
            self.optional["use-papers"] = optional["use-papers"]

    def flatten(self):
        try:
            if self.flattened:
                raise ValueError("Already flattened.")
        except AttributeError:
            if self.optional:
                self.__dict__.update(self.optional)

            if self.required:
                self.__dict__.update(self.required)

            self.startdate = pd.Timestamp(self.required["startdate"])
            self.flattened = True
        finally:
            return self

    def authors(self):
        authors = self.directors + self.coordinators + self.guests + self.advisors
        return set(map(str.lower, authors))

    def asdir(self):
        if os.environ.get("GITHUB_ACTIONS", "false") == "true":
            base = Path("/github/workspace")
        else:
            base = Path(str(self))

        return base / self.semester

    def __str__(self):
        return self.required["name"]

    def __repr__(self):
        return f"{self.required['name']}/{self.required['semester']}"
