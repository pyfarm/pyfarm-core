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

"""
Configuration Object
====================

Basic module used for reading configuration data into PyFarm
in various forms.

:const BOOLEAN_TRUE:
    set of values which will return a True boolean value from
    :func:`.read_env_bool`

:const BOOLEAN_FALSE:
    set of values which will return a False boolean value from
    :func:`.read_env_bool`
"""

import os
from ast import literal_eval
from errno import EEXIST
from functools import partial
from pprint import pformat
from string import Template
from itertools import product
from tempfile import gettempdir
from os.path import isfile, join, isdir, expanduser, expandvars, abspath

try:
    from StringIO import StringIO
except ImportError:  # pragma: no cover
    from io import StringIO

from pkg_resources import (
    DistributionNotFound, get_distribution, resource_filename)

import yaml
try:
    from yaml.loader import CLoader as Loader
except ImportError:  # pragma: no cover
    from yaml.loader import Loader

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import (
    STRING_TYPES, NUMERIC_TYPES, NOTSET, LINUX, MAC, WINDOWS, range_)

logger = getLogger("core.config")

# Boolean values as strings that can match a value we
# pulled from the environment after calling .lower().
BOOLEAN_TRUE = set(["1", "t", "y", "true", "yes"])
BOOLEAN_FALSE = set(["0", "f", "n", "false", "no"])


def read_env(envvar, default=NOTSET, warn_if_unset=False, eval_literal=False,
             raise_eval_exception=True, log_result=True, desc=None,
             log_defaults=False):
    """
    Lookup and evaluate an environment variable.

    :param string envvar:
        The environment variable to lookup in :class:`os.environ`

    :keyword object default:
        Alternate value to return if ``envvar`` is not present.  If this
        is instead set to ``NOTSET`` then an exception will be raised if
        ``envvar`` is not found.

    :keyword bool warn_if_unset:
        If True, log a warning if the value being returned is the same
        as ``default``

    :keyword eval_literal:
        if True, run :func:`.literal_eval` on the value retrieved
        from the environment

    :keyword bool raise_eval_exception:
        If True and we failed to parse ``envvar`` with :func:`.literal_eval`
        then raise a :class:`EnvironmentKeyError`

    :keyword bool log_result:
        If True, log the query and result to INFO.  If False, only log the
        query itself to DEBUG.  This keyword mainly exists so environment
        variables such as :envvar:`PYFARM_SECRET` or
        :envvar:`PYFARM_DATABASE_URI` stay out of log files.

    :keyword string desc:
        Describes the purpose of the value being returned.  This may also
        be read in at the time the documentation is built.

    :keyword bool log_defaults:
        If False, queries for envvars that have not actually been set and will
        just return ``default`` will not be logged
    """
    if envvar not in os.environ:
        # default not provided, raise an exception
        if default is NOTSET:
            raise EnvironmentError("$%s is not in the environment" % envvar)

        if warn_if_unset:  # pragma: no cover
            logger.warning("$%s is using a default value" % envvar)

        if log_defaults:
            if log_result:  # pragma: no cover
                logger.debug("read_env(%s): %s", (repr(envvar), repr(default)))
            else:
                logger.debug("read_env(%r) (value suppressed)", envvar)

        return default
    else:
        value = os.environ[envvar]

        if log_result:  # pragma: no cover
           logger.info("read_env(%r): %r", envvar, value)
        else:
           logger.debug("read_env(%r) (value suppressed)", envvar)


        if not eval_literal:
            return value

        try:
            return literal_eval(value)

        except (ValueError, SyntaxError) as e:
            if raise_eval_exception:
                raise

            args = (envvar, e)
            logger.error(
                "$%s contains a value which could not be parsed: %s" % args)
            logger.warning("returning default value for $%s" % envvar)
            return default


def read_env_bool(*args, **kwargs):
    """
    Wrapper around :func:`.read_env` which converts environment variables
    to boolean values.  Please see the documentation for
    :func:`.read_env` for additional information on exceptions and input
    arguments.

    :exception AssertionError:
        raised if a default value is not provided

    :exception TypeError:
        raised if the environment variable found was a string and could
        not be converted to a boolean.
    """
    notset = object()

    if len(args) == 1:
        kwargs.setdefault("default", notset)

    kwargs["eval_literal"] = False  # we'll handle this ourselves here
    value = read_env(*args, **kwargs)
    assert value is not notset, "default value required for `read_env_bool`"

    if isinstance(value, STRING_TYPES):
        value = value.lower()

        if value in BOOLEAN_TRUE:
            return True

        elif value in BOOLEAN_FALSE:
            return False

        else:
            raise TypeError(
                "could not convert %s to a boolean from $%s" % (
                    repr(value), args[0]))

    if not isinstance(value, bool):
        raise TypeError("expected a boolean default value for `read_env_bool`")

    return value


def read_env_number(*args, **kwargs):
    """
    Wrapper around :func:`.read_env` which will read a numerical value
    from an environment variable.  Please see the documentation for
    :func:`.read_env` for additional information on exceptions and input
    arguments.

    :exception TypeError:
        raised if we either failed to convert the value from the environment
        variable or the value was not a float, integer, or long
    """

    if len(args) == 1:
        kwargs.setdefault("default", NOTSET)

    kwargs["eval_literal"] = True
    try:
        value = read_env(*args, **kwargs)
    except ValueError:
        raise ValueError("failed to evaluate the data in $%s" % args[0])

    assert value is not NOTSET, "default value required for `read_env_number`"

    if not isinstance(value, NUMERIC_TYPES):
        raise TypeError("`read_env_number` did not return a number type object")

    return value


def read_env_strict_number(*args, **kwargs):
    """
    Strict version of :func:`.read_env_number` which will only return an integer

    :keyword number_type:
        the type of number(s) this function must return

    :exception AssertionError:
        raised if the number_type keyword is not provided (required to check
        the type on output)

    :exception TypeError:
        raised if the type of the result is not an instance of `number_type`
    """
    number_type = kwargs.pop("number_type", None)
    assert number_type is not None, "`number_type` keyword is required for"
    value = read_env_number(*args, **kwargs)

    if not isinstance(value, number_type):
        raise TypeError("%s is not an %s object" % (repr(value), number_type))

    return value


read_env_int = partial(read_env_strict_number, number_type=int)
read_env_float = partial(read_env_strict_number, number_type=float)


class Configuration(dict):
    """
    Main object responsible for finding, loading, and
    merging configuration data.  By default this class does nothing
    until :meth:`load` is called.  Once this method is called
    :class:`Configuration` class will populate itself with data loaded
    from the configuration files.  The configuration files themselves can
    be loaded from multiple location depending on the system's setup.  For
    example on Linux you might end up attempting to load these files for
    pyfarm.agent v1.2.3:

        Override paths set by ``DEFAULT_ENVIRONMENT_PATH_VARIABLE``.  By default
        this path will not be set, this is only an example.

        * ``/tmp/pyfarm/agent/1.2.3/agent.yml``
        * ``/tmp/pyfarm/agent/1.2/agent.yml``
        * ``/tmp/pyfarm/agent/1/agent.yml``
        * ``/tmp/pyfarm/agent/agent.yml``

        Paths relative to the current working directory or the directory
        provided to ``cwd`` when :class:`Configuration` was instanced.

        * ``etc/pyfarm/agent/1.2.3/agent.yml``
        * ``etc/pyfarm/agent/1.2/agent.yml``
        * ``etc/pyfarm/agent/1/agent.yml``
        * ``etc/pyfarm/agent/agent.yml``

        User's home directory

        * ``~/.pyfarm/agent/1.2.3/agent.yml``
        * ``~/.pyfarm/agent/1.2/agent.yml``
        * ``~/.pyfarm/agent/1/agent.yml``
        * ``~/.pyfarm/agent/agent.yml``

        System level paths

        * ``/etc/pyfarm/agent/1.2.3/agent.yml``
        * ``/etc/pyfarm/agent/1.2/agent.yml``
        * ``/etc/pyfarm/agent/1/agent.yml``
        * ``/etc/pyfarm/agent/agent.yml``

        Finally, if we don't locate a configuration file in any of
        the above paths we'll use the file which was installed along
        side the source code.

    :class:`Configuration` will only attempt to load data from files which
    exist on the file system when :meth:`load` is called.  If multiple files
    exist the data will be loaded from each file with the successive data
    overwriting the value from the previously loaded configuration file. So
    if you have two files containing the same data:

        * ``/etc/pyfarm/agent/agent.yml``

            .. code-block:: yaml

                env:
                    a: 0
                foo: 1
                bar: true


        * ``etc/pyfarm/agent/1.2.3/agent.yml``

            .. code-block:: yaml

                env:
                    a: 1
                    b: 1
                foo: 0

    You'll end up with a single merged configuration.  Please note that the
    only keys which will be merged in the configuration are the ``env`` key.
    Configuration files are meant to store simple data and while it can be
    used to store more complicate data it won't merge any other data
    structures.

        .. code-block:: yaml

            env:
                a: 1
                b: 1
            foo: 0
            bar: true

    :var string DEFAULT_SYSTEM_ROOT:
        The system level directory that we should look for configuration
        files in.  This path is platform dependent:

            * **Linux** - /etc/
            * **Mac** - /Library/
            * **Windows** - %ProgramData%.  An environment variable that
              varies depending on the Windows version.  See Microsoft's docs:
              https://www.microsoft.com/security/portal/mmpc/shared/variables.aspx

        The value built here will be copied onto the instance as ``system_root``

    :var string DEFAULT_USER_ROOT:
        The user level directory that we should look for configuration
        files in.  This path is platform dependent:

            * **Linux/Mac** - ~ (home directory)
            * **Windows** - %APPDATA%.  An environment variable that
              varies depending on the Windows version.  See Microsoft's docs:
              https://www.microsoft.com/security/portal/mmpc/shared/variables.aspx

        The value built here will be copied onto the instance as ``user_root``

    :var string DEFAULT_FILE_EXTENSION:
        The default file extension of the configuration files.  This will
        default to ``.yml`` and will be copied to ``file_extension`` when
        the class is instanced.

    :var string DEFAULT_LOCAL_DIRECTORY_NAME:
        A directory local to the current process which we should search
        for configuration files in.  This will default to ``etc`` and
        will be copied to ``local_dir`` when the class is instanced.

    :var string DEFAULT_PARENT_APPLICATION_NAME:
        The base name of the parent application.  This used used to build
        child directories and will default to ``pyfarm``.

    :var string DEFAULT_ENVIRONMENT_PATH_VARIABLE:
        A environment variable to search for a configuration path in.  The value
        defined here, which defaults to ``PYFARM_CONFIG_ROOT``, will be
        read from the environment when :class:`Configuration` is instanced.
        This allows for an non-standard configuration location to be loaded
        first for testing forced-override of the configuration.

    :var DEFAULT_TEMP_DIRECTORY_ROOT:
        The directory which will store any temporary files.

    :param string name:
        The name of the configuration itself, typically 'master' or
        'agent'.  This may also be the name of a package such
        as 'pyfarm.agent'.  When the package name is provided
        we can usually automatically determine the version
        number.

    :param string version:
        The version the version of the program running.

    :param string cwd:
        The current working directory to construct the local
        path from.  If not provided then we'll use :func:`os.getcwd`
        to determine the current working directory.

    .. automethod:: _expandvars
    """
    MAX_EXPANSION_RECURSION = 10

    if LINUX:  # pragma: no cover
        DEFAULT_SYSTEM_ROOT = join(os.sep, "etc")
        DEFAULT_USER_ROOT = expanduser("~")
    elif MAC:  # pragma: no cover
        DEFAULT_SYSTEM_ROOT = join(os.sep, "Library")
        DEFAULT_USER_ROOT = expanduser("~")
    elif WINDOWS:  # pragma: no cover
        DEFAULT_SYSTEM_ROOT = expandvars("$ProgramData")
        DEFAULT_USER_ROOT = expandvars("$APPDATA")
    else:  # pragma: no cover
        logger.warning("Failed to determine default configuration roots")
        DEFAULT_SYSTEM_ROOT = None
        DEFAULT_USER_ROOT = None

    DEFAULT_FILE_EXTENSION = ".yml"
    DEFAULT_LOCAL_DIRECTORY_NAME = "etc"
    DEFAULT_PARENT_APPLICATION_NAME = "pyfarm"
    DEFAULT_ENVIRONMENT_PATH_VARIABLE = "PYFARM_CONFIG_ROOT"
    DEFAULT_TEMP_DIRECTORY_ROOT = join(
        gettempdir(), DEFAULT_PARENT_APPLICATION_NAME)

    def __init__(self, name, version=None, cwd=None):
        super(Configuration, self).__init__()

        self._name = name
        self.loaded = ()
        self.cwd = os.getcwd() if cwd is None else cwd
        self.file_extension = self.DEFAULT_FILE_EXTENSION
        self.system_root = self.DEFAULT_SYSTEM_ROOT
        self.user_root = self.DEFAULT_USER_ROOT
        self.local_dir = join(self.cwd, self.DEFAULT_LOCAL_DIRECTORY_NAME)
        self.environment_root = read_env(
            self.DEFAULT_ENVIRONMENT_PATH_VARIABLE, None)

        # If `name` is an import name and an
        # explict version was not provided then try
        # to find one automatically.
        if version is None:
            try:
                self.distribution = get_distribution(name)

            except DistributionNotFound:
                raise ValueError(
                    "%r is not a Python package so you must provide "
                    "a version." % self._name)
            else:
                self.version = self.distribution.version

        else:
            self.distribution = None
            self.version = version

        self.name = self._name.split(".")[-1]

        self.child_dir = join(self.DEFAULT_PARENT_APPLICATION_NAME, self.name)
        self.tempdir = join(self.DEFAULT_TEMP_DIRECTORY_ROOT, self.name)

        # Create the base tempdir if it does not already
        # exist.  We're handling the exception instead of
        # using isdir() because it's possible multiple
        # processes could try to create the directory and
        # it's safer to let the file system handle it.
        try:
            os.makedirs(self.tempdir)
        except OSError as e:
            if e.errno != EEXIST:
                raise
        else:
            logger.debug("Created %r", self.tempdir)

        # Try to locate the package's built-in configuration
        # file.  This will be loaded before anything else
        # to provide the default values.
        try:
            self.package_configuration = resource_filename(
                name,
                join("etc", self._name.split(".")[-1] + self.file_extension))
        except ImportError:
            logger.warning(
                "Could not determine the default configuration file "
                "path for %s", self.name)
            self.package_configuration = None

    def split_version(self, sep="."):
        """
        Splits ``self.version`` into a tuple of individual versions.  For
        example ``1.2.3`` would be split into ``['1', '1.2', '1.2.3']``
        """
        if not self.version:
            return []

        split = self.version.split(sep)
        return list(reversed([
            sep.join(split[:index]) for index, _ in enumerate(split, start=1)]))

    def directories(self, validate=True, unversioned_only=False):
        """
        Returns a list of platform dependent directories which may contain
        configuration files.

        :param bool validate:
            When ``True`` this method will only return directories
            which exist on disk.

        :param bool unversioned_only:
            When ``True`` this method will only return versionless directories
            instead of both versionless and versioned directories.
        """
        roots = []
        versions = []

        if not unversioned_only:
            versions.extend(self.split_version())

        versions.append("")  # the 'version free' directory

        # If provided, insert the default root
        if self.system_root:  # could be empty in the environment
            roots.append(join(self.system_root, self.child_dir))

        # If provided, append the user directory
        if self.user_root:  # could be empty in the environment
            if not WINDOWS:
                roots.append(join(self.user_root, "." + self.child_dir))
            else:
                roots.append(join(self.user_root, self.child_dir))

        # If provided append a local directory
        if self.local_dir is not None:
            roots.append(join(self.local_dir, self.child_dir))

        # If provided, append the root discovered in the environment
        if self.environment_root is not None:
            roots.append(join(self.environment_root, self.child_dir))

        all_directories = []
        existing_directories = []

        for root, tail in product(roots, versions):
            directory = join(root, tail)
            all_directories.append(directory)

            if not validate or isdir(directory):
                existing_directories.append(directory)

        return existing_directories

    def files(self, validate=True, unversioned_only=False):
        """
        Returns a list of configuration files.

        :param bool validate:
            When ``True`` this method will only return files
            which exist on disk.

            .. note::

                This method calls :meth:`directories` and will
                be passed the value that is provided to ``validate``
                here.

        :param bool unversioned_only:
            See the keyword documentation for ``unversioned_only`` in
            :meth:`directories``
        """
        directories = self.directories(
            validate=validate, unversioned_only=unversioned_only)
        filename = self.name + self.file_extension
        existing_files = []

        if self.package_configuration is not None:
            if not validate or isfile(self.package_configuration):
                existing_files.append(self.package_configuration)

            else:
                logger.warning(
                    "%r does not have a default configuration file. Expected "
                    "to find %r but this path does not exist.",
                    self._name, self.package_configuration)

        for directory in directories:
            filepath = join(directory, filename)

            if not validate or isfile(filepath):
                existing_files.append(filepath)

        if not existing_files:  # pragma: no cover
            logger.error(
                "No configuration file(s) %s were found in %s",
                filename, pformat(directories))

        return existing_files

    def load(self, environment=None):
        """
        Loads data from the configuration files.  Any data present
        in the ``env`` key in the configuration files will update
        ``environment``

        :param dict environment:
            A dictionary to load data in the ``env`` key from
            the configuration files into.  This would typically be
            set to ``os.environ`` so the environment itself could
            be updated.
        """
        loaded = []

        for filepath in self.files():
            with open(filepath, "rb") as stream:
                try:
                    data = yaml.load(stream, Loader=Loader)

                except yaml.YAMLError as e:  # pragma: no cover
                    logger.error("Failed to load %r: %s", filepath, e)
                    continue

                else:
                    loaded.append(filepath)

            # Empty file
            if not data:
                continue

            if environment is not None and "env" in data:
                config_environment = data.pop("env")
                assert isinstance(config_environment, dict)
                environment.update(config_environment)

            elif environment is None:
                logger.warning(
                    "No environment was provided to be populated by the "
                    "configuration file(s)")

            # Update this instance with the loaded data
            self.update(data)

        if loaded:
            self.loaded = tuple(loaded)
            logger.info(
                "Loaded configuration file(s): %s", pformat(loaded))
        else:
            self.loaded = ()
            logger.warning(
                "No configuration files were loaded after searching %s",
                pformat(self.files(validate=False)))

    def _expandvars(self, value):
        """
        Performs variable expansion for ``value``. This method is run when
        a string value is returned from :meth:`get` or :meth:`__getitem__`.
        The default behavior of this method is to recursively expand
        variables using sources in the following order:

            * The environment, ``os.environ``
            * The environment (from the configuration), ``env``
            * Other values in the configuration
            * ``~`` to the user's home directory

        For example, the following configuration:

        .. code-block:: yaml

            foo: foo
            bar: bar
            foobar: $foo/$bar
            path: ~/$foobar/$TEST

        Would result in the following assuming ``$TEST`` is an
        environment variable set to ``somevalue`` and the current
        user's name is ``user``:

        .. code-block:: python

            {
                "foo": "foo",
                "bar": "bar",
                "foobar": "foo/bar",
                "path": "/home/user/foo/bar/somevalue"
            }
        """
        template_values = {"temp": self.tempdir}
        template_values.update(os.environ)
        template_values.update(self.get("env", {}))
        template_values.update(**self)

        # Do recursive variable expansion until we've either
        # reached MAX_EXPANSION_RECURSION or the resulting
        # value is unchanged
        for _ in range_(self.MAX_EXPANSION_RECURSION):
            template = Template(value)
            expanded = expanduser(template.safe_substitute(**template_values))

            # Nothing left to expand
            if value == expanded:
                break
            else:
                value = expanded

        return value

    def get(self, key, default=None):
        """
        Overrides :meth:`dict.get` to provide internal variable
        expansion through :meth:`_expandvars`.
        """
        value = super(Configuration, self).get(key, default)
        if isinstance(value, STRING_TYPES):
            value = self._expandvars(value)
        return value

    def __getitem__(self, item):
        """
        Overrides :meth:`dict.__getitem__` to provide internal variable
        expansion through :meth:`_expandvars`.
        """
        value = super(Configuration, self).__getitem__(item)
        if isinstance(value, STRING_TYPES):
            value = self._expandvars(value)
        return value
