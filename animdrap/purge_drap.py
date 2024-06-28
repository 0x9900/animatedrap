#! /usr/bin/env python
# vim:fenc=utf-8
#
# Copyright © 2024 fred <github-fred@hidzz.com>
#
# Distributed under terms of the BSD 3-Clause license.

"""
Purge old dlayer files
"""

import argparse
import logging
import os
import pathlib
import re
import sys
from datetime import datetime, timedelta, timezone


def purge_files(src_path, hours):
  start_date = datetime.now(timezone.utc) - timedelta(hours=hours)
  re_date = re.compile(r'^dlayer-(\d+T\d+).\w+').match

  for path in src_path.iterdir():
    if not (re_match := re_date(path.name)):
      continue
    date = datetime.strptime(re_match.group(1), '%Y%m%dT%H%M%S')
    date = date.replace(tzinfo=timezone.utc)
    if date >= start_date:
      logging.debug('Keep file: %s', path)
      continue
    logging.info('Purge file %s', path)
    path.unlink()


def type_path(arg: str) -> pathlib.Path:
  path = pathlib.Path(arg)
  if not path.is_dir():
    raise argparse.ArgumentTypeError(f'Error reading "{arg}"')
  return path


def main() -> None:
  log_file = None if os.isatty(sys.stdout.fileno()) else '/tmp/purge_drap.log'
  logging.basicConfig(
    format='%(asctime)s %(name)s:%(lineno)3d %(levelname)s - %(message)s', datefmt='%x %X',
    level=logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO')),
    filename=log_file
  )
  parser = argparse.ArgumentParser(description="purge d-rap files created by sunflu/dlayer")
  parser.add_argument('-H', '--hours', default=48, type=int,
                      help='Number of hours to animate (Default: %(default)s)')
  parser.add_argument('-s', '--source', default='/tmp/d-rap', type=type_path,
                      help=('Name of the directory where the images are located '
                            '(Default: %(default)s)'))
  opts = parser.parse_args()

  logging.info('Removeing files older than %d hours from %s', opts.hours, opts.source)
  purge_files(opts.source, opts.hours)


if __name__ == "__main__":
  main()
