#! /usr/local/bin/python
import os
import sys
sys.path.insert(1, '/usr/local/src/scons-2.1.0/engine')

from SCons import Script

BUILD_DIR = os.path.join(os.getenv('DEV_SRC'), 'cc', 'build')
Script.SConscript('SCONS', variant_dir=BUILD_DIR, src_dir='.', duplicate=0)
