#! /bin/env python3

from argparse import ArgumentParser
from subprocess import check_call
from pathlib import Path

import logging
import sys

API_LIST_BUILD_TARGET = 'generate_high_entropy_list'
API_LIST_FILE = 'high_entropy_list.csv'
API_LIST_TARGET_FILE = 'chromium_api_list.csv'


def Main():
    parser = ArgumentParser()
    parser.add_argument('--build_path', '-C', type=Path, required=True)
    parser.add_argument('--build',
                        '-B',
                        type=bool,
                        help='Whether the API list should be rebuilt',
                        default=False)
    parser.add_argument('--target_path', '-t', type=Path, default=Path.cwd())
    parser.add_argument(
        '--commmit',
        type=bool,
        default=False,
        help='Git commit after a successful extraction of the API list')

    args = parser.parse_args()

    if not args.build_path.exists():
        logging.critical('Build directory does not exist')
        sys.exit(1)

    if not args.target_path.exists():
        logging.critical('Target path does not exist')
        sys.exit(2)

    if args.build:
        logging.info(
            'Invoking autoninja to build {}'.format(API_LIST_BUILD_TARGET))
        check_call(['autoninja', API_LIST_BUILD_TARGET],
                   cwd=args.build_path.as_posix())

    api_list_file = args.build_path.joinpath(API_LIST_FILE)
    if not api_list_file.exists():
        logging.critical(
            'The API list file was not found at {}'.format(api_list_file))
        sys.exit(3)

    if not api_list_file.is_file():
        logging.critical('Unexpected file type for {}'.format(api_list_file))
        sys.exit(4)

    target_file = args.target_path.joinpath(API_LIST_TARGET_FILE)
    with api_list_file.open('r') as f:
        unordered_content = f.readlines()
        contents = [unordered_content[0]] + sorted(unordered_content[1:])
        with target_file.open('w') as w:
            w.writelines(contents)


if __name__ == "__main__":
    Main()
