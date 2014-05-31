# No shebang line, this module is meant to be imported
#
# Copyright 2013 Oliver Palmer
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import with_statement

import os
import tempfile
import uuid
from os.path import join
from random import randint

from pyfarm.core.enums import PY26, LINUX, MAC, WINDOWS
from pyfarm.core.testutil import TestCase as BaseTestCase

if PY26:
    from unittest2 import TestCase, skipIf
else:
    from unittest import TestCase, skipIf

from pyfarm.core.config import (
    read_env, read_env_number, read_env_bool, read_env_strict_number,
    BOOLEAN_FALSE, BOOLEAN_TRUE, configuration_directories, split_versions,
    DEFAULT_CONFIG_ROOT)


class TestConfig(TestCase):
    def test_readenv_missing(self):
        key = uuid.uuid4().hex
        with self.assertRaises(EnvironmentError):
            read_env(key)
        self.assertEqual(read_env(key, 42), 42)

    def test_readenv_exists(self):
        key = uuid.uuid4().hex
        value = uuid.uuid4().hex
        os.environ[key] = value
        self.assertEqual(read_env(key), value)
        del os.environ[key]

    def test_readenv_eval(self):
        key = uuid.uuid4().hex

        for value in (True, False, 42, 3.141, None, [1, 2, 3]):
            os.environ[key] = str(value)
            self.assertEqual(read_env(key, eval_literal=True), value)

        os.environ[key] = "f"
        with self.assertRaises(ValueError):
            read_env(key, eval_literal=True)

        self.assertEqual(
            read_env(key, 42, eval_literal=True, raise_eval_exception=False),
            42)

        del os.environ[key]

    def test_read_env_bool(self):
        for true in BOOLEAN_TRUE:
            key = uuid.uuid4().hex
            os.environ[key] = true
            self.assertTrue(read_env_bool(key, False))

        for false in BOOLEAN_FALSE:
            key = uuid.uuid4().hex
            os.environ[key] = false
            self.assertFalse(read_env_bool(key, True))

        with self.assertRaises(AssertionError):
            read_env_bool("")

        with self.assertRaises(TypeError):
            key = uuid.uuid4().hex
            os.environ[key] = "42"
            read_env_bool(key, 1)

        with self.assertRaises(TypeError):
            key = uuid.uuid4().hex
            self.assertTrue(read_env_bool(key, 1))

        key = uuid.uuid4().hex
        self.assertTrue(read_env_bool(key, True))

    def test_read_env_number(self):
        key = uuid.uuid4().hex
        os.environ[key] = "42"
        self.assertEqual(read_env_number(key), 42)
        key = uuid.uuid4().hex
        os.environ[key] = "3.14159"
        self.assertEqual(read_env_number(key), 3.14159)

        key = uuid.uuid4().hex
        os.environ[key] = "foo"
        with self.assertRaises(ValueError):
            self.assertEqual(read_env_number(key))

        key = uuid.uuid4().hex
        os.environ[key] = "None"
        with self.assertRaises(TypeError):
            self.assertEqual(read_env_number(key))

    def test_read_env_strict_number(self):
        with self.assertRaises(AssertionError):
            read_env_strict_number("")

        key = uuid.uuid4().hex
        os.environ[key] = "3.14159"
        self.assertEqual(read_env_strict_number(key, number_type=float),
                         3.14159)

        key = uuid.uuid4().hex
        os.environ[key] = "42"
        with self.assertRaises(TypeError):
            read_env_strict_number(key, number_type=float)


class TestVersionSplit(TestCase):
    def test_split(self):
        self.assertEqual(split_versions("1.2.3"), ["1", "1.2", "1.2.3"])

    def test_custom_split(self):
        self.assertEqual(
            split_versions("1-2-3", sep="-"), ["1", "1-2", "1-2-3"])


class TestConfigDirectory(BaseTestCase):
    def setUp(self):
        super(TestConfigDirectory, self).setUp()
        self.env_key = "a" + uuid.uuid4().hex
        self.env_value = "a" + uuid.uuid4().hex
        self.version = ".".join(
            list(map(str, [randint(1, 10), randint(1, 10), randint(1, 10)])))
        self.version_split = split_versions(self.version)
        self.child_dir = join("a" + uuid.uuid4().hex, "a" + uuid.uuid4().hex)
        self.local_dir = "a" + uuid.uuid4().hex
        self.system_root = "/a" + uuid.uuid4().hex
        self.environment_root = "a" + uuid.uuid4().hex
        os.environ[self.env_key] = self.env_value

    def test_basic_output(self):
        self.assertEqual(
            configuration_directories(
                self.version, self.child_dir, local_dir=self.local_dir,
                environment_root=self.environment_root,
                system_root=self.system_root, filter_missing=False),
            [join(self.system_root, self.child_dir + "/"),
             join(self.system_root, self.child_dir, self.version_split[0]),
             join(self.system_root, self.child_dir, self.version_split[1]),
             join(self.system_root, self.child_dir, self.version_split[2]),
             join(self.environment_root, self.child_dir + "/"),
             join(self.environment_root, self.child_dir, self.version_split[0]),
             join(self.environment_root, self.child_dir, self.version_split[1]),
             join(self.environment_root, self.child_dir, self.version_split[2]),
             join(self.local_dir, self.child_dir + "/"),
             join(self.local_dir, self.child_dir, self.version_split[0]),
             join(self.local_dir, self.child_dir, self.version_split[1]),
             join(self.local_dir, self.child_dir, self.version_split[2])])

    def test_filter_missing(self):
        tempdir = tempfile.mkdtemp()
        subdirs = [
            join(tempdir, self.child_dir) + "/",
            join(tempdir, self.child_dir, "1"),
            join(tempdir, self.child_dir, "1.2"),
            join(tempdir, self.child_dir, "1.2.3")]

        for subdir in subdirs:
            try:
                os.makedirs(subdir)
            except OSError:
                pass

            self.add_cleanup_path(subdir)

        self.assertEqual(
            subdirs,
            configuration_directories(
                "1.2.3", self.child_dir,
                system_root=tempdir, environment_root=None))

    @skipIf(not WINDOWS, "not windows")
    def test_windows_system_root(self):
        self.assertEqual(DEFAULT_CONFIG_ROOT, os.environ["APPDATA"])

    @skipIf(not LINUX, "not linux")
    def test_linux_system_root(self):
        self.assertEqual(DEFAULT_CONFIG_ROOT, join(os.sep, "etc"))

    @skipIf(not MAC, "not mac")
    def test_mac_system_root(self):
        self.assertEqual(DEFAULT_CONFIG_ROOT, join(os.sep, "Library"))
