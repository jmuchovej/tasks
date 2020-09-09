import importlib

from invoke import Collection

from . import src

ns = Collection("autobot")

# To avoid having to manually specify packages, do some import magick and let
#   PyInvoke figure the rest out
for subpkg in src.__all__:
    # https://stackoverflow.com/questions/46205467/python-importlib-no-module-named
    subpkg = importlib.import_module(f".src.{subpkg}", package=__package__)
    ns.add_collection(subpkg)
