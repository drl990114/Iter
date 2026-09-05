import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description="Count Markdown notes in a folder")
parser.add_argument("directory", type=Path)
args = parser.parse_args()
print(sum(1 for path in args.directory.iterdir() if path.is_file() and path.suffix == ".md"))
