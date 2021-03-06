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
from google.protobuf.text_format import Parse, MessageToString
from google.protobuf.message import Message
from blink_apis_pb2 import Snapshot, ExtendedAttributes, HighEntropyType, \
    IDLType, SourceLocation, InterfaceLike, Dictionary, Enumeration, Operation, Typedef

import logging
import sys
import shutil
from csv import DictWriter
from typing import Dict, List

API_LIST_BUILD_TARGET = 'blink_apis'
API_LIST_FILE = 'blink_apis.textpb'
API_LIST_TARGET_CSV_FILE = 'chromium_api_list.csv'


def GetExtendedAttributes(exts: ExtendedAttributes,
                          d: Dict[str, str]) -> Dict[str, str]:
    if exts.secure_context:
        d['secure_context'] = 'True'
    if exts.high_entropy == HighEntropyType.HIGH_ENTROPY_UNCLASSIFIED:
        d['high_entropy'] = '(True)'
    elif exts.high_entropy == HighEntropyType.HIGH_ENTROPY_DIRECT:
        d['high_entropy'] = 'Direct'
    if exts.use_counter:
        d['use_counter'] = exts.use_counter
    if exts.secure_context:
        d['secure_context'] = 'True'
    return d


def GetIdlType(idl_type: IDLType, d: Dict[str, str]) -> Dict[str, str]:
    d['idl_type'] = idl_type.idl_type_string
    return d


def GetSourceLocation(source_location: SourceLocation,
                      d: Dict[str, str]) -> Dict[str, str]:
    if source_location.filename:
        d['source_file'] = source_location.filename
    if source_location.line and source_location.line > 0:
        d['source_line'] = str(source_location.line)


def ProtobufToCanonicalList(snapshot: Snapshot) -> Dict[str, str]:
    l: List[Dict[str, str]] = []

    for interface in snapshot.interfaces:
        d = {'interface': interface.name, 'entity_type': 'interface'}
        GetExtendedAttributes(interface.extended_attributes, d)
        GetSourceLocation(interface.source_location, d)
        l.append(d)

        for attr in interface.attributes:
            d = {
                'interface': interface.name,
                'name': attr.name,
                'entity_type': 'attribute'
            }
            GetExtendedAttributes(attr.extended_attributes, d)
            GetIdlType(attr.idl_type, d)
            GetSourceLocation(attr.source_location, d)
            l.append(d)

        for op in interface.operations:
            d = {
                'interface': interface.name,
                'name': op.name,
                'entity_type': 'operation'
            }
            GetExtendedAttributes(op.extended_attributes, d)
            GetIdlType(op.return_type, d)
            GetSourceLocation(op.source_location, d)
            d['arguments'] = '(' + ','.join(
                [t.idl_type_string for t in op.arguments]) + ')'
            l.append(d)

        for c in interface.constants:
            d = {
                'interface': interface.name,
                'name': c.name,
                'entity_type': 'constant'
            }
            GetIdlType(c.idl_type, d)
            GetSourceLocation(c.source_location, d)
            l.append(d)

    def KeyFunc(d: Dict[str, str]):
        return d.get('interface', '') + ':' + d.get('name', '')

    return sorted(l, key=KeyFunc)


def CanonicalizeSnapshot(snapshot: Snapshot):
    def NameOrSelf(message: Message):
        return message.name

    def Canonicalize(message: Message):
        for (fd, v) in message.ListFields():
            if fd.label != fd.LABEL_REPEATED:
                continue
            # Order of arguments is fixed.
            if fd.name == 'arguments':
                continue
            for item in v:
                if isinstance(item, Message):
                    Canonicalize(item)
            if len(v) == 0:
                continue
            if isinstance(v[0], Message):
                v.sort(key=NameOrSelf)
            else:
                v.sort()

    Canonicalize(snapshot)


def WriteSnapshotAsCsv(snapshot: Snapshot, csv_path: Path):
    with csv_path.open('w', encoding='utf-8') as f:
        fields = [
            'interface', 'name', 'entity_type', 'arguments', 'idl_type',
            'syntactic_form', 'use_counter', 'secure_context', 'high_entropy',
            'source_file', 'source_line'
        ]
        writer = DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(ProtobufToCanonicalList(snapshot))


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

    commit_hash = str(check_output(['git', 'rev-parse', 'HEAD'],
                                   cwd=args.build_path),
                      encoding='utf-8').strip()
    commit_position = str(check_output(
        ['git', 'footers', '--position', 'HEAD'],
        cwd=args.build_path.parent.parent),
                          encoding='utf-8').strip()

    target_file = args.target_path.joinpath(API_LIST_TARGET_CSV_FILE)
    with api_list_file.open('r') as f:
        snapshot = Snapshot()
        Parse(f.read(), snapshot)

    if not snapshot.chromium_revision:
        snapshot.chromium_revision = commit_hash
    CanonicalizeSnapshot(snapshot)
    WriteSnapshotAsCsv(snapshot, target_file)

    with args.target_path.joinpath(API_LIST_FILE).open('w') as f:
        f.write(MessageToString(snapshot, as_utf8=True, indent=2))

    if args.commit:
        git_status = str(check_output(['git', 'status', '--porcelain=v1'],
                                      cwd=args.target_path),
                         encoding='utf-8').splitlines()
        should_commit = True

        if len(git_status) == 0:
            logging.info('No change to API list')
            should_commit = False

        for s in git_status:
            if s.split()[1] not in [API_LIST_FILE, API_LIST_TARGET_CSV_FILE]:
                logging.error(
                    f'Unexpected changes found in the repository:"{s}"'
                    '. Those changes should be committed separately from the '
                    'ones introduced by this tool')
                should_commit = False
                break
        if should_commit:
            commit_message = f'''Blink API list update from {commit_position!s}

Source Chromium revision is https://crrev.com/{commit_hash!s}

See https://github.com/asankah/chromium-api-list for details on how the
list was generated.
'''
            check_call([
                'git', 'commit', '-m', commit_message, '--',
                API_LIST_TARGET_CSV_FILE, API_LIST_FILE
            ],
                       cwd=args.target_path)


if __name__ == "__main__":
    Main()
