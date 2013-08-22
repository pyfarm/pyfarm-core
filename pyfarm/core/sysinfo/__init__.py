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
Top level module which provides information about the operating system,
system memory, network, and processor related information.  Unlike other
modules in PyFarm this module is not generally meant to be overridden outside
the package.
"""

# NOTE: OperatingSystemInfo should be instanced first so other subpackages can
# use it

from pyfarm.core.sysinfo.osdata import OperatingSystemInfo
from pyfarm.core.sysinfo.memory import MemoryInfo
from pyfarm.core.sysinfo.network import NetworkInfo
from pyfarm.core.sysinfo.processor import ProcessorInfo
from pyfarm.core.sysinfo.user import username, isAdmin

osinfo = OperatingSystemInfo()
meminfo = MemoryInfo()
cpuinfo = ProcessorInfo()
netinfo = NetworkInfo()