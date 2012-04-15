# Copyright 2012 Arunjit Singh. All Rights Reserved.
"""Tests for ccbuild."""

__author__ = 'Arunjit Singh <arunjit@me.com>'

import unittest

import ccbuild


class CCBuildTest(unittest.TestCase):

  def testNameResolution(self):
    basepath = '/Users/arunjitsingh/Developer/src/cc/net'
    resolve = ccbuild.ResolveBuildPath
    self.assertEqual(resolve(basepath, ':socket'),
                     '//cc/net:socket')
    self.assertEqual(resolve(basepath, 'tcp:connection'),
                     '//cc/net/tcp:connection')
    self.assertEqual(resolve(basepath, '//cc/base64:encoder'),
                     '//cc/base64:encoder')


if __name__ == '__main__':
  unittest.main()
