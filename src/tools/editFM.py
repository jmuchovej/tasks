from pathlib import Path

from ruamel.yaml import YAML

yaml = YAML()


class EditableFM:
    def __init__(self, base_path: Path, delim: str = "---"):
        self.base_path = Path(base_path)
        self.delim = delim

    def load(self, file: Path):
        self.fm = []
        self.content = []

        self.path = self.base_path / file

        file = open(self.path, "r").readlines()

        lineno = 0
        delims_seen = 0
        for line in file:
            if line.startswith(self.delim):
                delims_seen += 1
            else:
                if delims_seen < 2:
                    self.fm.append(line)
                else:
                    self.content.append(line)

        # Parse YAML, trying to preserve comments and whitespace
        self.fm = yaml.load("".join(self.fm))

    def dump(self):
        assert self.path, "You need to `.load()` first."

        with open(self.path, "w") as f:
            f.write(f"{self.delim}\n")
            yaml.dump(self.fm, f)
            f.write(f"{self.delim}\n")
            f.writelines(self.content)
