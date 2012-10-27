#! /usr/bin/env python
# Copyright 2012 Arunjit Singh. All Rights Reserved.

"""Build tool for C++.

An easy to use builder for C++ projects and source trees.

The build configuration is written in JSON, and unlike GYP, it actually compiles
and builds source and dependencies.

The flag --devroot defines the base from where the build starts. If not given,
searches for a file, ".devroot", in the parent directories of the current
directory, stopping at $HOME or /usr/local. It expects the usual directories,
"src", "include", "lib", "build" and "bin" to exist there, though it may not
use all of them. Only the "src" directory is required; "build" is created if it
doesn't exist. "src" becomes the source base.

Build configurations can be specified in $HOME/.ccbuild.json. It is recommended
that this file includes all non-standard flags, include paths and library paths
applicable to all builds.

EXAMPLE:
  $ ccbuild //cc/net:socket             # :socket is a library target
  Source: <devroot/src>/cc/net/{build.json, socket.h, socket.cc}
  Build: <devroot>/build/cc/net/socket.dylib

  $ ccbuild --run //cc/net:socket_try   # :socket_try is a binary target
  Source: <devroot/src>/cc/net/{build.json, :socket, socket_try.cc}
  Build: <devroot>/build/cc/net/{socket.dylib, socket_try*}
  Run: <devroot>/build/cc/net/socket_try

  Arguments can be passed to binary targets by using '--' followed by the args.

  // = <devroot/src>
  * = executable
"""

__author__ = 'Arunjit Singh <arunjit@me.com>'

import json
import logging
import os
import re
import subprocess
import sys

import gflags

try:
  from ajpylib import logger
except ImportError:
  logging.warning('ajpylib.logger is not available')
  pass

gflags.DEFINE_string('devroot', '', 'Root dir. Must include a "src" dir')
gflags.DEFINE_bool('debug', False, 'Enable debugging logs')
gflags.DEFINE_bool('dryrun', False, 'Don\'t execute anything')
gflags.DEFINE_bool('run', False, 'Execute a binary target')
gflags.DEFINE_bool('test', False, 'Execute a test target')
gflags.DEFINE_bool('quiet', False, 'Quieten output to above warnings')
gflags.DEFINE_list('binargs', [], 'Arguments to pass to a binary target')

_LOG = logging.getLogger('ccbuild')

# Alias gflags' FLAGS for ease of use
FLAGS = gflags.FLAGS

# The CWD
CWD = os.getcwd()

# The user's home dir
HOME = os.getenv('HOME')

# The C++ compiler
CXX = os.getenv('CXX', 'clang++')

COMMON_FLAGS = ['-Wall']
DEBUG_FLAGS = ['-g']
COMMON_LIBS = ['stdc++']


# Error codes (for where 0==success)
[NO_ERROR, CMDARG_ERROR, BUILD_ERROR, SUBPROCESS_ERROR] = range(4)


def main(argv):
  try:
    argv = FLAGS(argv)[1:]
  except gflags.FlagsError, e:
    print('%s\nUsage: %s ARGS\n%s' % (e, sys.argv[0], FLAGS))
    return CMDARG_ERROR
  if not argv:
    raise BuildError('No build target specified')
  if FLAGS.dryrun:
    FLAGS.debug = True
  if FLAGS.debug:
    _LOG.setLevel(_LOG.DEBUG)
  if FLAGS.quiet or FLAGS.test:
    _LOG.setLevel(_LOG.WARNING)
  if FLAGS.run and '--' in argv:
    FLAGS.binargs = argv[argv.index('--') + 1:]
  # Configure devroot, srcbase, buildbase based on flags
  # Configure build values based on $HOME/.ccbuild.json
  # Do some work
  return NO_ERROR


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except BuildError as error:
    _LOG.error(error)
    sys.exit(BUILD_ERROR)
  except subprocess.CalledProcessError as error:
    _LOG.error('A sub-process errored: %s', error)
    sys.exit(SUBPROCESS_ERROR)
