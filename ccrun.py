#!/usr/local/bin/python
# Copyright 2012 Arunjit Singh. All Rights Reserved.
"""Execute a binary in the BUILD_BASE using a SRC_BASE path.

Doesn't build the binary.
"""

__author__ = 'Arunjit Singh <arunjit@me.com>'

import os
import re
import subprocess
import sys

BUILD_BASE = os.path.join(os.getenv('DEV_SRC'), 'build')


def main(argv):
  if len(argv) < 2:
    raise ArgumentError('Not enough arguments')
  target = re.sub(r'^//', BUILD_BASE + os.sep, argv[1], count=1)
  target = re.sub(':', os.sep, target)
  binargs = []
  if len(argv) > 2:
    binargs = argv[2:]
  subprocess.call([target] + binargs)


if __name__ == '__main__':
  main(sys.argv)

