#!/usr/bin/env python3
"""Print the source/contract fingerprint to attach to execution evidence."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from task_logic import candidate_sha256

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle')
    args = parser.parse_args()
    print(candidate_sha256(json.loads(Path(args.bundle).read_text())))
