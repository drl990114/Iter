import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description="Count Markdown notes in a folder")
parser.add_argument("directory", type=Path)
parser.add_argument(
    "--recursive",
    action="store_true",
    help="Include Markdown notes in nested folders",
)
args = parser.parse_args()
paths = args.directory.rglob("*.md") if args.recursive else args.directory.iterdir()
print(sum(1 for path in paths if path.is_file() and path.suffix == ".md"))
