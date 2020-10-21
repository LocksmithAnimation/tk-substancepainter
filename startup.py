# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sys
import shutil
import hashlib
import socket
from distutils.version import LooseVersion

##############

import sgtk
from sgtk.platform import SoftwareLauncher, SoftwareVersion, LaunchInformation


__author__ = "Diego Garcia Huerta"
__contact__ = "https://www.linkedin.com/in/diegogh/"

logger = sgtk.LogManager.get_logger(__name__)


# note that this is the same in engine.py
MINIMUM_SUPPORTED_VERSION = "6.2"


def to_new_version_system(version):
    """
    Converts a version string into a new style version.

    New version system was introduced in version 2020.1, that became
    version 6.1.0, so we need to do some magic to normalize versions.
    https://docs.substance3d.com/spdoc/version-2020-1-6-1-0-194216357.html

    The way we support this new version system is to use LooseVersion for
    version comparisons. We modify the major version if the version is higher 
    than 2017.1.0 for the version to become in the style of 6.1, by literally
    subtracting 2014 to the major version component.
    This leaves us always with a predictable version system:
        2.6.2  -> 2.6.2 (really old version)
        2017.1 -> 3.1
        2018.0 -> 4.0
        2020.1 -> 6.1 (newer version system starts)
        6.2    -> 6.2 ...

    2017.1.0 represents the first time the 2k style version was introduced
    according to:
    https://docs.substance3d.com/spdoc/all-changes-188973073.html

    Note that this change means that the LooseVersion is good for comparisons 
    but NEVER for printing, it would simply print the same version as 
    LooseVersion does not support rebuilding of the version string from it's 
    components
    """

    version = LooseVersion(str(version))

    if version >= LooseVersion("2017.1"):
        version.version[0] -= 2014
    return version


class SubstancePainterLauncher(SoftwareLauncher):
    """
    Handles launching SubstancePainter executables. Automatically starts up
    a tk-substancepainter engine with the current context in the new session
    of SubstancePainter.
    """

    # Named regex strings to insert into the executable template paths when
    # matching against supplied versions and products. Similar to the glob
    # strings, these allow us to alter the regex matching for any of the
    # variable components of the path in one place.

    # It seems that Substance Painter does not use any version number in the
    # installation folders, as if they do not support multiple versions of
    # the same software.
    COMPONENT_REGEX_LOOKUP = {}

    # This dictionary defines a list of executable template strings for each
    # of the supported operating systems. The templates are used for both
    # globbing and regex matches by replacing the named format placeholders
    # with an appropriate glob or regex string.

    EXECUTABLE_TEMPLATES = {
        "darwin": ["/Applications/Allegorithmic/Substance Painter.app"],
        "win32": ["C:/Program Files/Allegorithmic/Substance Painter/Substance Painter.exe"],
        "linux2": [
            "/usr/Allegorithmic/Substance Painter",
            "/usr/Allegorithmic/Substance_Painter/Substance Painter",
            "/opt/Allegorithmic/Substance_Painter/Substance Painter",
        ],
    }

    @property
    def minimum_supported_version(self):
        """
        The minimum software version that is supported by the launcher.
        """
        return MINIMUM_SUPPORTED_VERSION

    def prepare_launch(self, exec_path, args, file_to_open=None):
        """
        Prepares an environment to launch SubstancePainter in that will automatically
        load Toolkit and the tk-substancepainter engine when SubstancePainter starts.

        :param str exec_path: Path to SubstancePainter executable to launch.
        :param str args: Command line arguments as strings.
        :param str file_to_open: (optional) Full path name of a file to open on
                                            launch.
        :returns: :class:`LaunchInformation` instance
        """
        required_env = {}

        # Run the engine's startup plugin when Substance Painter starts up
        # by adding it the plugins path
        required_env["SUBSTANCE_PAINTER_PLUGINS_PATH"] = self.disk_location

        # Add any additional shelf paths to the environment. By itself, this 
        # does nothing (this is not a variable recognised by Substance Painter), 
        # but it is picked up by the substancepainter_initialize Rez package and 
        # added (by editing the Windows registry).
        shelf_path = self.get_setting("shelf_path")
        if shelf_path is not None:
            required_env["LSA_SUBSTANCE_PAINTER_PROJECT_SHELF"] = shelf_path

        # Prepare the launch environment with variables required by the
        # classic bootstrap approach.
        self.logger.debug(
            "Preparing SubstancePainter Launch via Toolkit Classic methodology ..."
        )

        required_env["TK_DEBUG"] = os.environ.get("TK_DEBUG") and "true" or ""

        if file_to_open:
            # Add the file name to open to the launch environment
            required_env["SGTK_FILE_TO_OPEN"] = file_to_open

        # First big disclaimer: qml does not support environment variables for safety reasons
        # the only way to pass information inside substance painter is to actually encode
        # as a string and trick the program to think it is opening a substance painter project
        # The reason why this works is because inside substance painter the original file is
        # used with an URL, ie. //file/serve/filename, so we add to the URL using & to pass
        # our now fake environment variables.
        # Only the startup script, the location of python and potentially the file to open
        # are needed.
        args = ""
        args = ["%s=%s" % (k, v) for k, v in required_env.items()]
        args = '"&%s"' % "&".join(args)
        logger.info("running %s" % args)

        required_env["SGTK_ENGINE"] = self.engine_name
        required_env["SGTK_CONTEXT"] = sgtk.context.serialize(self.context)

        # args = '&SGTK_SUBSTANCEPAINTER_ENGINE_STARTUP=%s;SGTK_SUBSTANCEPAINTER_ENGINE_PYTHON=%s' % (startup_path, sys.executable)
        return LaunchInformation(exec_path, args, required_env)

    def _icon_from_engine(self):
        """
        Use the default engine icon as substancepainter does not supply
        an icon in their software directory structure.

        :returns: Full path to application icon as a string or None.
        """

        # the engine icon
        engine_icon = os.path.join(self.disk_location, "icon_256.png")
        return engine_icon

    def _is_supported(self, sw_version):
        """
        Inspects the supplied :class:`SoftwareVersion` object to see if it
        aligns with this launcher's known product and version limitations. Will
        check the :meth:`~minimum_supported_version` as well as the list of
        product and version filters.
        :param sw_version: :class:`SoftwareVersion` object to test against the
            launcher's product and version limitations.
        :returns: A tuple of the form: ``(bool, str)`` where the first item
            is a boolean indicating whether the supplied :class:`SoftwareVersion` is
            supported or not. The second argument is ``""`` if supported, but if
            not supported will be a string representing the reason the support
            check failed.
        This helper method can be used by subclasses in the :meth:`scan_software`
        method.

        To check if the version is supported:
        
        First we make an exception for cases were we cannot retrieve the 
        version number, we accept the software as valid.

        Second, checks against the minimum supported version. If the
        supplied version is greater it then checks to ensure that it is in the
        launcher's ``versions`` constraint. If there are no constraints on the
        versions, we will accept the software version.

        :param str version: A string representing the version to check against.
        :return: Boolean indicating if the supplied version string is supported.
        """

        # we support cases were we could not extract the version number
        # from the binary/executable
        if sw_version.version == UNKNOWN_VERSION:
            return (True, "")

        # convert to new version system if required
        version = to_new_version_system(sw_version.version)

        # second, compare against the minimum version
        if self.minimum_supported_version:
            min_version = to_new_version_system(self.minimum_supported_version)

            if version < min_version:
                # the version is older than the minimum supported version
                return (
                    False,
                    "Executable '%s' didn't meet the version requirements, "
                    "%s is older than the minimum supported %s"
                    % (sw_version.path, sw_version.version, self.minimum_supported_version),
                )

        # third if the version is new enough, we check if we have any
        # version restrictions
        if not self.versions:
            # No version restriction. All versions supported
            return (True, "")

        # if so, check versions list
        supported = sw_version.version in self.versions
        if not supported:
            return (
                False,
                "Executable '%s' didn't meet the version requirements"
                "(%s not in %s)" % (sw_version.path, sw_version.version, self.versions),
            )

        # passed all checks. must be supported!
        return (True, "")

    def scan_software(self):
        """
        Scan the filesystem for substancepainter executables.

        :return: A list of :class:`SoftwareVersion` objects.
        """
        self.logger.debug("Scanning for SubstancePainter executables...")

        supported_sw_versions = []
        for sw_version in self._find_software():
            (supported, reason) = self._is_supported(sw_version)

            if supported:
                supported_sw_versions.append(sw_version)
            else:
                self.logger.debug(
                    "SoftwareVersion %s is not supported: %s" % (sw_version, reason)
                )

        return supported_sw_versions

    def _find_software(self):
        """
        Find executables in the default install locations.
        """
        from rez import packages_

        # all the discovered executables
        sw_versions = []

        for package in packages_.iter_packages("substancepainter"):
            self.logger.debug(
                "Software found: %s | %s.",
                str(package.version),
                package.executable,
            )
            sw_versions.append(
                SoftwareVersion(
                    str(package.version),
                    "Substance Painter",
                    package.executable,
                    self._icon_from_engine(),
                )
            )

        return sw_versions
