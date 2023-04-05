import runpy
from pathlib import Path
from setuptools import setup, find_packages

root = Path(__file__).resolve().parent

with open(root / "README.md", encoding="utf-8") as f:
    long_description = f.read()


def parse_reqs(name):
    with open(root / "requirements" / name, "r") as f:
        return f.readlines()


reporting_reqs = parse_reqs("reporting.txt")

all_reqs = reporting_reqs

name = "omniscripts"
version = runpy.run_path(root / name / "__version__.py")["__version__"]


setup(
    name="omniscripts",
    version=version,
    description="Benchmarks for data frame processing libraries",
    long_description=long_description,
    url="https://github.com/intel-ai/omniscripts/",
    packages=find_packages(exclude=["scripts", "scripts.*"]),
    # I suggest we migrate from requirements.yaml to requirements.txt and just put these file here:
    install_requires=parse_reqs("base.txt"),
    extras_require={"reporting": reporting_reqs, "all": all_reqs},
    python_requires=">=3.8",
)