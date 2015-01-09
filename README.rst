.. Copyright 2013 Oliver Palmer
..
.. Licensed under the Apache License, Version 2.0 (the "License");
.. you may not use this file except in compliance with the License.
.. You may obtain a copy of the License at
..
..   http://www.apache.org/licenses/LICENSE-2.0
..
.. Unless required by applicable law or agreed to in writing, software
.. distributed under the License is distributed on an "AS IS" BASIS,
.. WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
.. See the License for the specific language governing permissions and
.. limitations under the License.

PyFarm Core
===========

.. image:: https://travis-ci.org/pyfarm/pyfarm-core.svg?branch=master
    :target: https://travis-ci.org/pyfarm/pyfarm-core
    :alt: build status (master)

.. image:: https://coveralls.io/repos/pyfarm/pyfarm-core/badge?branch=master
    :target: https://coveralls.io/r/pyfarm/pyfarm-core?branch=master
    :alt: coverage

This library contains core modules, classes, and data types which are
used by other parts of the PyFarm project.  This package is contains:

    * A configuration module for loading and merging configuration
      files from disk.
    * Enumerations of basic system information such as interpreter information,
      Python types, operating systems and other basic information that can
      be shared across the project.
    * Logger setup and handling
    * Miscellaneous utilities

Python Version Support
----------------------

This library supports Python 2.6+ and 3.2+ in one code base.  Python 2.5
and lower is not supported due to significant syntax, library and other
differences.  This library must support the range of Python versions
that ``python.master`` and ``pyfarm.agent`` supports.


Documentation
-------------

The documentation for this this library is hosted on
`Read The Docs <https://pyfarm.readthedocs.org/projects/pyfarm-core/en/latest/>`_.
It's generated directly from this library using sphinx (setup may vary depending
on platform)::

    virtualenv env
    . env/bin/activate
    pip install sphinx nose
    pip install -e . --egg
    make -C docs html



Testing
-------

Tests are run on `Travis <https://travis-ci.org/pyfarm/pyfarm-core>`_ for
every commit.  They can also be run locally too (setup may vary depending
on platform)::

    virtualenv env
    . env/bin/activate
    pip install nose
    pip install -e . --egg
    nosetests tests/
