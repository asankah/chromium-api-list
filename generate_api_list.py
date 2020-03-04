#! /bin/env python3

# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
        commit_hash = str(
            check_output(['git', 'rev-parse', 'HEAD'],
                         cwd=args.build_path), encoding='utf-8').strip()
        commit_position = str(check_output(
            ['git', 'footers', '--position', 'HEAD'],
            cwd=args.build_path.parent.parent),
                              encoding='utf-8').strip()

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
            commit_message = '''Blink API list update from {commit_position!s}

Source Chromium revision is https://crrev.com/{commit_hash!s}

See https://github.com/asankah/chromium-api-list for details on how the
list was generated.
'''.format(commit_position=commit_position, commit_hash=commit_hash)
            check_call([
                'git', 'commit', '-m', commit_message, '--',
                API_LIST_TARGET_FILE
            ],
                       cwd=args.target_path)


if __name__ == "__main__":
    Main()
