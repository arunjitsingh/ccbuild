#!/usr/local/bin/python
# Copyright 2012 Arunjit Singh. All Rights Reserved.
"""Build tool for C++.

An easy to use builder for C++ projects and source trees.

The build configuration is written in JSON, and unlike GYP, it actually compiles
and builds source and dependencies.

This version of the tool is currently limited to only my source tree, in that
the source and build paths are kind of hard-coded. In principle, this is more
useful for source trees than a single project, but maybe I'll update this to
specify a "root" for a [project] source tree or have it be pre-configured in a
file somewhere.

All sources are resolved from SRC_BASE. Built products go under SRC_BASE/build.

EXAMPLE:
  $ ccbuild //cc/net:socket             # :socket is a library target
  Source: SRC_BASE/cc/net/{build.json, socket.h, socket.cc}
  Build: SRC_BASE/build/cc/net/socket.dylib

  $ ccbuild --run //cc/net:socket_try   # :socket_try is a binary target
  Source: SRC_BASE/cc/net/{build.json, :socket, socket_try.cc}
  Build: SRC_BASE/build/cc/net/{socket.dylib, socket_try*}
  Run: SRC_BASE/build/cc/net/socket_try

  Arguments can be passed to binary targets by using '--' followed by the args.

  // = SRC_BASE
  * = executable


Author: Arunjit Singh <arunjit@me.com>
"""

__author__ = 'Arunjit Singh <arunjit@me.com>'

import gflags
import json
import os
import re
import subprocess
import sys

from ajpylib.logger import logger

# Alias gflags' FLAGS for ease of use
FLAGS = gflags.FLAGS

# The CWD
CWD = os.getcwd()

# The C++ compiler
CXX = 'clang++'

# The development root, essentially like a $PREFIX. Expects these
# sub-directories: include, lib, src
DEV_ROOT = os.getenv('DEV_ROOT')

SRC_BASE = os.path.join(DEV_ROOT, 'src')
BUILD_BASE = os.path.join(SRC_BASE, 'build')

SYS_INCLUDES = ['/include', '/usr/include', '/usr/local/include']
SYS_LIBPATHS = ['/usr/lib', '/usr/local/lib']

COMMON_FLAGS = ['-Wall']
DEBUG_FLAGS = ['-g']
COMMON_LIBS = ['stdc++']

INCLUDES = SYS_INCLUDES
LIBPATHS = [os.path.join(DEV_ROOT, 'lib')] + SYS_LIBPATHS


if not os.path.isdir(BUILD_BASE):
  os.mkdir(BUILD_BASE)


def ResolveBuildPath(base, pathspec):
  if pathspec.startswith('//'):
    return pathspec
  elif pathspec.startswith(':'):
    return ResolveBuildPath(base, base + pathspec)
  elif pathspec.startswith('/'):
    return re.sub(SRC_BASE + '/', '//', pathspec, count=1)
  else:
    return ResolveBuildPath(base, os.path.join(base, pathspec))


class BuildError(Exception):
  pass


def GetSrc(path):
  return re.sub(r'^//', SRC_BASE + '/', path, count=1)


def GetBuild(path):
  return re.sub(r'^//', BUILD_BASE + '/', path, count=1)


def GetBuildForTarget(path):
  path = GetSrc(os.path.join(path, 'build.json'))
  build_file = None
  try:
    build_file = open(path, 'r')
    build_json = build_file.read()
    return json.loads(build_json)
  except IOError:
    raise BuildError('"%s" was not readable' % path)
  except ValueError:
    raise BuildError('Invalid JSON syntax in "%s"' % path)
  finally:
    if build_file:
      build_file.close()


def ExecuteCommand(command, outfile=None):
  logger.debug(' '.join(command))
  if FLAGS.dryrun:
    return 0
  if outfile:
    outdir = os.path.dirname(outfile)
    if not os.path.isdir(outdir):
      os.makedirs(outdir, 0755)
  return subprocess.check_call(command)


def CompileLibrary(name, dirname, srcs):
  # command: CXX -o OUT -c -fPIC COMMON_FLAGS srcs
  out = GetBuild(os.path.join(dirname, name) + '.os')
  flags = map(lambda i: '-I' + i, INCLUDES)
  flags.extend(COMMON_FLAGS)
  srcs = map(lambda s: GetSrc(s), srcs)
  command = [CXX, '-o', out]
  command.extend(['-c', '-fPIC'])
  command.extend(flags)
  command.extend(srcs)
  if ExecuteCommand(command, out) == 0:
    logger.info('Compiled library "%s:%s"', dirname, name)
  return out


def LinkLibrary(name, dirname, libs, comps):
  out = GetBuild(os.path.join(dirname, name) + '.dylib')
  ldflags = map(lambda l: '-L' + l, LIBPATHS)
  libs.extend(COMMON_LIBS)
  libs = map(lambda l: '-l' + l, libs)
  command = [CXX, '-o', out]
  command.extend(['-dynamiclib'])
  command.extend(ldflags)
  command.extend(libs)
  command.extend(comps)
  if ExecuteCommand(command, out) == 0:
    logger.info('Linked library "%s:%s"', dirname, name)
  return out


def CompileBinary(name, dirname, srcs):
  # command: CXX -o OUT -c COMMON_FLAGS srcs
  out = GetBuild(os.path.join(dirname, name) + '.o')
  flags = map(lambda i: '-I' + i, INCLUDES)
  srcs = map(lambda s: GetSrc(s), srcs)
  command = [CXX, '-o', out, '-c']
  command.extend(flags)
  command.extend(srcs)
  if ExecuteCommand(command, out) == 0:
    logger.info('Compiled binary "%s:%s"', dirname, name)
  return out


def LinkBinary(name, dirname, libs, comps):
  out = GetBuild(os.path.join(dirname, name))
  ldflags = map(lambda l: '-L' + l, LIBPATHS)
  libs = map(lambda l: '-l' + l, libs)
  command = [CXX, '-o', out]
  command.extend(ldflags)
  command.extend(libs)
  command.extend(comps)
  if ExecuteCommand(command, out) == 0:
    logger.info('Linked binary "%s:%s"', dirname, name)
  return out


class Build(object):
  """."""

  _build_map = {}

  def __init__(self, target):
    logger.info('Building "%s"', target)
    target_path, target_name = tuple(target.split(':'))
    self.targets = GetBuildForTarget(target_path)
    self.target = self.targets.get(target_name)
    if not self.target:
      raise BuildError('Target "%s" not found' % target)

    self.target_type = self.target.get('type')
    if not self.target_type:
      raise BuildError('Every target needs a type')

    def _Mapper(p):
      return ResolveBuildPath(target_path, p)
    self.srcs = map(_Mapper, self.target.get('srcs', []))
    self.deps = map(_Mapper, self.target.get('deps', []))

    self.libs = self.target.get('libs', [])

    logger.debug('target: %s', self.target)
    logger.debug('srcs: %s', self.srcs)
    logger.debug('deps: %s', self.deps)

    self.library = None
    self.binary = None

    self.compiled_libs = []
    if self.deps:
      for dep in self.deps:
        b = Build(dep)
        if not b.library:
          raise BuildError('Cannot link a target that isn\'t a library')
        self.compiled_libs.append(b.library)

    if self.target_type == 'library':
      comp = CompileLibrary(target_name, target_path, self.srcs)  # deps?
      srcs = self.compiled_libs + [comp]
      self.library = LinkLibrary(target_name, target_path, self.libs, srcs)
    elif self.target_type in ('binary', 'test'):
      comp = CompileBinary(target_name, target_path, self.srcs)
      srcs = self.compiled_libs + [comp]
      self.binary = LinkBinary(target_name, target_path, self.libs, srcs)


def InitializeBuild(target):
  build = Build(target)
  if build.binary and (FLAGS.run or FLAGS.test):
    ExecuteCommand([build.binary] + FLAGS.binargs)


def Setup(srcbase, buildbase):
  global SRC_BASE, BUILD_BASE, INCLUDES
  SRC_BASE = srcbase
  BUILD_BASE = buildbase

  local_includes = [os.path.join(DEV_ROOT, 'include'), SRC_BASE]

  INCLUDES = local_includes + SYS_INCLUDES

#  logger.info('Source base: "%s"', SRC_BASE)
#  logger.info('Build base: "%s"', BUILD_BASE)
#  logger.info('Includes: "%s"', INCLUDES)

gflags.DEFINE_string('srcbase', SRC_BASE, 'The source base (SRC_BASE)')
gflags.DEFINE_string('buildbase', BUILD_BASE, 'The build base')
gflags.DEFINE_bool('debug', True, 'Enable debugging logs')
gflags.DEFINE_bool('dryrun', False, 'Don\'t execute anything')
gflags.DEFINE_bool('run', False, 'Execute a binary target')
gflags.DEFINE_bool('test', False, 'Execute a test target')
gflags.DEFINE_bool('quiet', False, 'Quieten output to above warnings')

gflags.DEFINE_list('binargs', [], 'Arguments to pass to a binary target')

def main(argv):
  try:
    argv = FLAGS(argv)[1:]
  except gflags.FlagsError, e:
    print('%s\nUsage: %s ARGS\n%s' % (e, sys.argv[0], FLAGS))
    sys.exit(1)
  if not argv:
    raise BuildError('No build target specified')
  if FLAGS.dryrun:
    FLAGS.debug = True
  if FLAGS.debug:
    logger.setLevel(logger.DEBUG)
  if FLAGS.quiet or FLAGS.test:
    logger.setLevel(logger.WARNING)
  if FLAGS.run and '--' in argv:
    FLAGS.binargs = argv[argv.index('--') + 1:]
  Setup(FLAGS.srcbase, FLAGS.buildbase)
  target = ResolveBuildPath(CWD, argv[0])
  # `target` is an absolute path to a build target.
  InitializeBuild(target)
  return 0


if __name__ == '__main__':
  try:
    main(sys.argv)
  except BuildError as error:
    logger.error(error)
    sys.exit(1)
  except subprocess.CalledProcessError as error:
    logger.error('A sub-process errored: %s', error)
    sys.exit(2)
