import importlib

from sgtk.platform.qt import QtGui, QtCore
import substance_painter
import substance_painter_plugins
from substancepainter_core.toolbar_registry import ToolbarRegistry


class ToolbarGenerator(object):
    def __init__(self, engine):
        self._engine = engine
        self.toolbar_handle = substance_painter.ui.add_toolbar(
            "Locksmith Toolbar", "ls_substance_toolbar"
        )
        self.plugin_actions = []
        self.toolbar_commands = []

    def cleanup(self):
        for plugin_action in self.plugin_actions:
            ToolbarRegistry.get_registry().remove_action(plugin_action)
        substance_painter.ui.delete_ui_element(self.toolbar_handle)

    def create_toolbar(self):
        self.toolbar_commands = self._engine.get_setting("toolbar_commands", [])
        if not self.toolbar_commands:
            return
        self.toolbar_handle.clear()
        for (cmd_name, cmd_details) in self._engine.commands.items():
            if cmd_name in self.toolbar_commands:
                self.add_shotgun_action(cmd_name, cmd_details)
        self.add_plugin_actions()

    def add_divider(self):
        divider = QtGui.QAction(self.toolbar_handle)
        divider.setSeparator(True)
        self.toolbar_handle.addAction(divider)
        return divider

    def add_shotgun_action(self, cmd_name, cmd_details):
        action = None
        if cmd_details["properties"]["icons"]["dark"]["png"]:
            icon = QtGui.QIcon(cmd_details["properties"]["icons"]["dark"]["png"])
            action = QtGui.QAction(icon, "", self.toolbar_handle)
        self.toolbar_handle.addAction(action)
        action.triggered.connect(cmd_details["callback"])
        action.setToolTip(cmd_name)
        action.setStatusTip(cmd_name)
        return action

    def add_plugin_actions(self):
        self.plugin_actions = self.get_plugin_actions()
        if self.plugin_actions:
            self.add_divider()
        for plugin_action in self.plugin_actions:
            plugin_action.setParent(self.toolbar_handle)
            self.toolbar_handle.addAction(plugin_action)

    def get_plugin_actions(self):
        plugin_actions = []
        plugins_names = substance_painter_plugins.plugin_module_names()
        for plugin_name in plugins_names:
            try:
                plugin = importlib.import_module(plugin_name)
                actions = plugin.get_toolbar_actions()
                if actions:
                    plugin_actions.extend(actions)
            except AttributeError:
                continue
        return plugin_actions