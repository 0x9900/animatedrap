#! /usr/bin/env python
# vim:fenc=utf-8
#
# Copyright © 2024 fred <github-fred@hidzz.com>
#
# Distributed under terms of the BSD 3-Clause license.

"""
Transform the d-layer absorption png files into an animation
See the solar activity website @ https://bsdworld.org/
"""

import argparse
import atexit
import logging
import os
import pathlib
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from subprocess import PIPE, Popen

WORKDIR_NAME = 'workdir'
FFMPEG = shutil.which('ffmpeg')


def cleanup(path: pathlib.Path) -> None:
  """Remove the working directory"""
  if not path.exists():
    return
  logging.info('Cleanup %s', path)
  for fname in path.glob('*'):
    fname.unlink()
  path.rmdir()


def mk_workdir(source: pathlib.Path) -> pathlib.Path:
  path = source.joinpath(WORKDIR_NAME)
  path.mkdir()
  return path


def type_path(arg: str) -> pathlib.Path:
  path = pathlib.Path(arg)
  if not path.is_dir():
    raise argparse.ArgumentTypeError(f'Error reading "{arg}"')
  return path


def select_files(source: pathlib.Path, work_dir: pathlib.Path, hours: int) -> None:
  re_date = re.compile(r'.*dlayer-(\d+).png').match
  start = datetime.now(timezone.utc) - timedelta(hours=hours)
  for fname in sorted(source.glob('dlayer-*.png')):
    match = re_date(str(fname))
    if not match:
      continue
    date = datetime.strptime(match.group(1), '%Y%m%d%H%M')
    date = date.replace(tzinfo=timezone.utc)
    if date >= start:
      workfile = work_dir.joinpath(fname.name)
      logging.debug('Selecting %s -> %s', fname, workfile)
      workfile.hardlink_to(fname)


def mk_video(work_dir: pathlib.Path, video_file: pathlib.Path) -> None:
  logfile = pathlib.Path('/tmp/ffmpeg-drap.log')
  tmp_file = work_dir.joinpath(f'd-rat-{os.getpid()}.mp4')
  pngfiles = work_dir.joinpath('dlayer-*.png')

  in_args = f'-y -framerate 6 -pattern_type glob -i {pngfiles}'.split()
  ou_args = '-c:v libx264 -pix_fmt yuv420p -vf scale=800:400'.split()
  cmd = [FFMPEG, *in_args, *ou_args, str(tmp_file)]

  logging.info('Writing ffmpeg output in %s', logfile)
  logging.info("Saving %s video file", tmp_file)
  with logfile.open("a", encoding='ascii') as err:
    err.write(' '.join(cmd))
    err.write('\n\n')
    err.flush()
    with Popen(cmd, shell=False, stdout=PIPE, stderr=err) as proc:
      proc.wait()
    if proc.returncode != 0:
      logging.error('Error generating the video file')
      return
    logging.info('mv %s %s', tmp_file, video_file)
    tmp_file.rename(video_file)


def main() -> None:

  log_file = None if os.isatty(sys.stdout.fileno()) else '/tmp/animdrap.log'

  logging.basicConfig(
    format='%(asctime)s %(name)s:%(lineno)3d %(levelname)s - %(message)s', datefmt='%x %X',
    level=logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO')),
    filename=log_file
  )

  parser = argparse.ArgumentParser(description="Animate the d-rap files created by sunflu/dlayer")
  parser.add_argument('-H', '--hours', default=48, type=int,
                      help='Number of hours to animate (Default: %(default)s)')
  parser.add_argument('-s', '--source', default='/tmp/d-rap', type=type_path,
                      help='Name of the videofile to geneate (Default: %(default)s)')
  parser.add_argument('-t', '--target', default='/tmp/dlayer.mp4',
                      help='Name of the videofile to geneate (Default: %(default)s)')
  opts = parser.parse_args()

  work_dir = mk_workdir(opts.source)
  atexit.register(cleanup, work_dir)
  select_files(opts.source, work_dir, opts.hours)
  mk_video(work_dir, opts.target)
  cleanup(work_dir)


if __name__ == "__main__":
  main()
