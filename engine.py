import os
import sys
import inspect
import logging
import traceback
from distutils.version import LooseVersion

import sgtk
from sgtk.platform import Engine
from tank.platform.constants import TANK_ENGINE_INIT_HOOK_NAME

import substance_painter


SHOW_COMP_DLG = "SGTK_COMPATIBILITY_DIALOG_SHOWN"
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


class SubstancePainterEngine(Engine):

    def __init__(self, *args, **kwargs):
        """
        Engine Constructor
        """
        self._menu_generator = None
        self._toolbar_generator = None
        self.toolbar_commands = []
        self._shutting_down = False
        self.__qt_panels = {}
        self.__qt_dialogs = []
        super(SubstancePainterEngine, self).__init__(*args, **kwargs)

    @property
    def register_toggle_debug_command(self):
        """
        Indicates whether the engine should have a toggle debug logging
        command registered during engine initialization.
        :rtype: bool
        """
        return True

    @property
    def context_change_allowed(self):
        """
        Whether the engine allows a context change without the need for a
        restart.
        """
        return True

    @property
    def host_info(self):
        """
        :returns: A dictionary with information about the application hosting 
                  his engine.

        The returned dictionary is of the following form on success:

            {
                "name": "SubstancePainter",
                "version": "2018.3.1",
            }

        The returned dictionary is of following form on an error preventing
        the version identification.

            {
                "name": "SubstancePainter",
                "version: "unknown"
            }
        """
        host_info = {"name": "SubstancePainter", "version": "unknown"}
        try:
            from application_core.windows import WindowsFileDetails
            details = WindowsFileDetails(sys.executable)
            host_info["version"] = ".".join((str(x) for x in details.file_version))
        except:
            pass
        return host_info

    def pre_app_init(self):
        """
        Initializes the Substance Painter engine.
        """

        self.logger.debug("%s: Initializing...", self)
        self.tk_substancepainter = self.import_module("tk_substancepainter")
        self.utils = self.tk_substancepainter.utils
        
        # check that we are running an ok version of Substance Painter
        current_os = sys.platform
        if current_os not in ["darwin", "win32", "linux64"]:
            raise sgtk.TankError(
                "The current platform is not supported!"
                " Supported platforms "
                "are Mac, Linux 64 and Windows 64."
            )

        # default menu name is Shotgun but this can be overridden
        # in the configuration to be sgtk in case of conflicts
        self._menu_name = "Shotgun"
        if self.get_setting("use_sgtk_as_menu_name", False):
            self._menu_name = "Sgtk"

        # New version system was introduced in version 2020.1, that became
        # version 6.1.0, so we need to do some magic to normalize versions.
        # https://docs.substance3d.com/spdoc/version-2020-1-6-1-0-194216357.html
        painter_version_str = self.host_info["version"]
        painter_version = to_new_version_system(painter_version_str)
        painter_min_supported_version = to_new_version_system(MINIMUM_SUPPORTED_VERSION)

        if painter_version < painter_min_supported_version:
            msg = (
                "Shotgun integration is not compatible with Substance Painter versions"
                " older than %s" % MINIMUM_SUPPORTED_VERSION
            )
            raise sgtk.TankError(msg)

        if painter_version > painter_min_supported_version:
            if current_os.startswith("win"):
                self.logger.debug(
                    "Substance Painter on Windows can deadlock if QtWebEngineWidgets "
                    "is imported. Setting "
                    "SHOTGUN_SKIP_QTWEBENGINEWIDGETS_IMPORT=1..."
                )
                os.environ["SHOTGUN_SKIP_QTWEBENGINEWIDGETS_IMPORT"] = "1"

    def post_app_init(self):
        sgtk.platform.engine.set_current_engine(self)
        self.create_shotgun_menu()
        self.create_shotgun_toolbar()

        from sgtk.platform.qt import QtCore
        app = QtCore.QCoreApplication.instance()
        app.aboutToQuit.connect(self.destroy)

        # emit an engine started event
        self.sgtk.execute_core_hook(TANK_ENGINE_INIT_HOOK_NAME, engine=self)

    def destroy_engine(self):
        """
        Cleanup after ourselves
        """
        self.logger.debug("Destroying Substance Painter Engine")
        self.close_windows()
        if self._menu_generator:
            self._menu_generator.cleanup()
            self._menu_generator = None
        if self._toolbar_generator:
            self._toolbar_generator.cleanup()
            self._toolbar_generator = None

    def _create_dialog(self, title, bundle, widget, parent):
        dialog = super(SubstancePainterEngine, self)._create_dialog(title, bundle, widget, parent)
        self._apply_external_styleshet(self, dialog)
        qss = dialog.styleSheet()
        qss = qss.replace("{{ENGINE_ROOT_PATH}}", self.disk_location)
        dialog.setStyleSheet(qss)
        dialog.update()
        return dialog

    def create_shotgun_menu(self):
        """
        Creates the main Shotgun menu in Substance Painter.
        """
        if not self._menu_generator:
            self._menu_generator = self.tk_substancepainter.MenuGenerator(
                self, self._menu_name)
            substance_painter.ui.add_menu(self._menu_generator.menu_handle)
        self._menu_generator.create_menu()

    def create_shotgun_toolbar(self):
        """
        Creates a Shotgun toolbar in Substance Painter
        """
        if not self._toolbar_generator:
            self._toolbar_generator = self.tk_substancepainter.ToolbarGenerator(self)
        self._toolbar_generator.create_toolbar()

    def _get_dialog_parent(self):
        """
        Get the QWidget parent for all dialogs created through :meth:`show_dialog` :meth:`show_modal`.

        :return: QT Parent window (:class:`PySide.QtGui.QWidget`)
        """
        return substance_painter.ui.get_main_window()

    def show_dialog(self, title, bundle, widget_class, *args, **kwargs):
        """
        Shows a non-modal dialog window in a way suitable for this engine.
        The engine will attempt to parent the dialog nicely to the host
        application.

        :param title: The title of the window
        :param bundle: The app, engine or framework object that is associated
            with this window
        :param widget_class: The class of the UI to be constructed. This must
            derive from QWidget.

        Additional parameters specified will be passed through to the
        widget_class constructor.

        :returns: the created widget_class instance
        """
        if not self.has_ui:
            self.logger.error(
                "Sorry, this environment does not support UI display! Cannot "
                "show the requested window '%s'." % title
            )
            return None

        # create the dialog:
        dialog, widget = self._create_dialog_with_widget(
            title, bundle, widget_class, *args, **kwargs
        )

        self.__qt_dialogs.append(dialog)

        self.logger.debug("Showing dialog: %s" % (title,))
        dialog.show()

        return widget

    def show_panel(self, panel_id, title, bundle, widget_class, *args, **kwargs):
        if panel_id in self.__qt_panels:
            dock_widget = self.__qt_panels[panel_id]
        else:
            dialog, widget = self._create_dialog_with_widget(
                title, bundle, widget_class, *args, **kwargs
            )
            dialog.setObjectName(panel_id)
            dock_widget = substance_painter.ui.add_dock_widget(dialog)
            self.__qt_panels[panel_id] = dock_widget
        dock_widget.show()

        return dock_widget

    def __get_platform_resource_path(self, filename):
        """
        Returns the full path to the given platform resource file or folder.
        Resources reside in the core/platform/qt folder.
        :return: full path
        """
        tank_platform_folder = os.path.abspath(inspect.getfile(sgtk.platform))
        return os.path.join(tank_platform_folder, "qt", filename)

    def _emit_log_message(self, handler, record):
        if record.levelno < logging.INFO:
            formatter = logging.Formatter("Debug: Shotgun %(basename)s: %(message)s")
        else:
            formatter = logging.Formatter("Shotgun %(basename)s: %(message)s")

        msg = formatter.format(record)

        if record.levelno < logging.WARNING:
            fct = substance_painter.logging.info
        elif record.levelno < logging.ERROR:
            fct = substance_painter.logging.warning
        else:
            fct = substance_painter.logging.error

        self.async_execute_in_main_thread(fct, msg)

    def close_windows(self):
        """
        Closes the various windows (dialogs, panels, etc.) opened by the
        engine.
        """

        for dialog in self.__qt_dialogs:
            dialog.hide()
            dialog.setParent(None)
            dialog.deleteLater()

        # Make a copy of the list of Tank dialogs that have been created by the
        # engine and are still opened since the original list will be updated
        # when each dialog is closed.
        opened_panel_list = list(self.__qt_panels.keys())

        # Loop through the list of opened Tank dialogs.
        for panel_id in opened_panel_list:
            panel = self.__qt_panels.pop(panel_id)
            panel_window_title = panel.windowTitle()
            try:
                self.logger.debug("Closing dialog %s", panel_window_title)
                panel.widget().close()
                substance_painter.ui.delete_ui_element(panel)
            except Exception as exception:
                traceback.print_exc()
                self.logger.error(
                    "Cannot close dialog %s: %s", panel_window_title, exception
                )