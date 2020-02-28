#! /bin/env python3

from argparse import ArgumentParser
from subprocess import check_call, check_output
from pathlib import Path

import logging
import sys

API_LIST_BUILD_TARGET = 'generate_high_entropy_list'
API_LIST_FILE = 'high_entropy_list.csv'
API_LIST_TARGET_FILE = 'chromium_api_list.csv'

COMMIT_POSITION_HEADER = 'Cr-Commit-Position: '


def Main():
    parser = ArgumentParser()
    parser.add_argument('--build_path', '-C', type=Path, required=True)
    parser.add_argument('--build',
                        '-B',
                        action='store_true',
                        help='Whether the API list should be rebuilt')
    parser.add_argument('--target_path', '-t', type=Path, default=Path.cwd())
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument(
        '--commit',
        action='store_true',
        help='Git commit after a successful extraction of the API list')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if not args.build_path.exists():
        logging.critical('Build directory does not exist. Checked {}'.format(
            args.build_path))
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

    if args.commit:
        commit_position = check_output(['git', 'rev-parse', 'HEAD'],
                                       cwd=args.build_path)
        commit_message = check_output(['git', 'cat-file', '-p', 'HEAD'],
                                      cwd=args.build_path).splitlines()
        for l in commit_message:
            ls = l.decode()
            if ls.startswith(COMMIT_POSITION_HEADER):
                commit_position = ls[len(COMMIT_POSITION_HEADER):].strip()
                break

        git_status = str(check_output(['git', 'status', '--porcelain=v1'],
                                      cwd=args.target_path),
                         encoding='utf-8').splitlines()
        if len(git_status) == 0:
            logging.info('No change to API list')
        elif len(git_status) != 1:
            logging.error(
                'There is more than one changed file in the repository. ' +
                'Can\'t commit changes.')
        elif git_status[0].split() != ['M', API_LIST_TARGET_FILE]:
            logging.error(
                'Unexpected changes found in the repository: "{}"'.format(
                    git_status[0]))
        else:
            check_call([
                'git', 'commit', '-m',
                '\'API list update from {}\''.format(commit_position), '--',
                API_LIST_TARGET_FILE
            ],
                       cwd=args.target_path)


if __name__ == "__main__":
    Main()
