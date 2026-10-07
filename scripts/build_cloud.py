"""Build static cloud UI from an explicit list; never copy local data."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
FILES = ('index.html','app.js','style.css','mark.svg')


def main():
    destination=ROOT/'cloud-dist'
    destination.mkdir(exist_ok=True)
    for name in FILES:
        shutil.copyfile(ROOT/'cloud/web'/name,destination/name)
    print('Cloud UI built from 4 public source files. No local data included.')


if __name__=='__main__':main()
