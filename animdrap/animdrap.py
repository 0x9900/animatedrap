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
from typing import Iterator

WORKDIR_NAME = '-workdir'


def counter(start: int = 1) -> Iterator[str]:
  cnt = start
  while True:
    yield f'{cnt:06d}'
    cnt += 1


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


def select_files(source: pathlib.Path, style: str, work_dir: pathlib.Path, hours: int) -> None:
  count = counter()
  re_date = re.compile(rf'.*dlayer-(\d+T\d+)-{style}.png').match
  start = datetime.now(timezone.utc) - timedelta(hours=hours)
  for fname in sorted(source.glob('dlayer-*.png')):
    match = re_date(str(fname))
    if not match:
      continue
    date = datetime.strptime(match.group(1), '%Y%m%dT%H%M%S')
    date = date.replace(tzinfo=timezone.utc)
    if date >= start:
      workfile = work_dir.joinpath(f'dlayer-{next(count)}.png')
      workfile.hardlink_to(fname)
      logging.debug('Selecting %s -> %s', fname, workfile)


def mk_video(work_dir: pathlib.Path, video_file: pathlib.Path) -> None:
  ffmpeg = shutil.which('ffmpeg')
  if not ffmpeg:
    raise FileNotFoundError('ffmpeg not found')

  logfile = pathlib.Path('/tmp/ffmpeg-drap.log')
  tmp_file = work_dir.joinpath(f'd-rap-{os.getpid()}.mp4')
  pngfiles = work_dir.joinpath('dlayer-*.png')

  in_args = f'-y -framerate 6 -pattern_type glob -i {pngfiles}'.split()
  ou_args = '-c:v libx264 -pix_fmt yuv420p -vf scale=800:400'.split()
  cmd = [ffmpeg, *in_args, *ou_args, str(tmp_file)]

  logging.debug(' '.join(cmd))

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


def mk_link(src, dst):
  if dst.exists():
    dst.unlink()
  os.link(src, dst)
  logging.info('Link %s ->  %s', src, dst)


def main() -> None:

  log_file = None if os.isatty(sys.stdout.fileno()) else '/tmp/animdrap.log'

  logging.basicConfig(
    format='%(asctime)s %(name)s:%(lineno)3d %(levelname)s - %(message)s', datefmt='%x %X',
    level=logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO')),
    filename=log_file
  )

  parser = argparse.ArgumentParser(description="Animate the d-rap files created by sunflux/dlayer")
  parser.add_argument('-H', '--hours', default=48, type=int,
                      help='Number of hours to animate (Default: %(default)s)')
  parser.add_argument('-s', '--source', required=True, type=pathlib.Path,
                      help='Name of the videofile to geneate (Default: %(default)s)')
  parser.add_argument('-t', '--target_dir', type=pathlib.Path, default='/tmp',
                      help='Name of the videofile to geneate (Default: %(default)s)')
  opts = parser.parse_args()

  for style in ('light', 'dark'):
    work_dir = mk_workdir(opts.source)
    atexit.register(cleanup, work_dir)
    select_files(opts.source, style, work_dir, opts.hours)
    target_file = opts.target_dir.joinpath(f'dlayer-{style}').with_suffix('.mp4')
    mk_video(work_dir, target_file)
    if style == 'light':
      mk_link(target_file, target_file.parent.joinpath('dlayer.mp4'))
    cleanup(work_dir)


if __name__ == "__main__":
  main()
