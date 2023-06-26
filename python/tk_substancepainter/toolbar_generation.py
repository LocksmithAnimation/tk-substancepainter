import importlib
import copy

from sgtk.platform.qt import QtGui, QtCore
import substance_painter
import substance_painter_plugins
import substancepainter_core  # import populates the ToolbarRegistry
from substancepainter_core.toolbar_registry import ToolbarRegistry, get_icon_path


class ToolbarGenerator(object):
    def __init__(self, engine):
        self._engine = engine
        self.toolbar_handle = substance_painter.ui.add_toolbar(
            "Locksmith Toolbar", "ls_substance_toolbar"
        )
        self.plugin_actions = []
        self.tool_actions = []
        self.shotgun_actions = []
        self.tool_actions = []

    def cleanup(self):
        self.toolbar_handle.clear()
        for action in self.shotgun_actions:
            substance_painter.ui.delete_ui_element(action)
        for action in self.tool_actions:
            substance_painter.ui.delete_ui_element(action)
        self.shotgun_actions = []
        self.plugin_actions = []
        self.tool_actions = []
        substance_painter.ui.delete_ui_element(self.toolbar_handle)
        self.toolbar_handle = None

    def create_action(
        self, action_id, callback, icon=None, tooltip=None, action_type="tools"
    ):
        if icon:
            icon = QtGui.QIcon(icon)
            action = QtGui.QAction(icon, action_id)
        else:
            action = QtGui.QAction(action_id)
        self.toolbar_handle.addAction(action)
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
        action.triggered.connect(callback)
        return action

    def add_divider(self):
        divider = QtGui.QAction(self.toolbar_handle)
        divider.setSeparator(True)
        self.toolbar_handle.addAction(divider)
        return divider

    def add_shotgun_action(self, cmd_name, cmd_details):
        action = self.create_action(
            "",
            cmd_details["callback"],
            cmd_details["properties"]["icons"]["dark"]["png"],
            cmd_name,
        )
        self.shotgun_actions.append(action)

        return action

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

    def add_plugin_actions(self):
        self.plugin_actions = self.get_plugin_actions()
        if self.plugin_actions:
            self.add_divider()
        for plugin_action in self.plugin_actions:
            plugin_action.setParent(self.toolbar_handle)
            self.toolbar_handle.addAction(plugin_action)

    def add_tool_actions(self):
        tool_actions = ToolbarRegistry.get_registry().toolbar_actions
        if tool_actions:
            self.add_divider()
        for action_id, action_data in tool_actions.items():
            action_data = copy.copy(action_data)
            action_data["icon"] = (
                action_data["icon"]
                and get_icon_path(f"{action_data['icon']}.png").as_posix()
            )
            tool_action = self.create_action(action_id, **action_data)
            self.toolbar_handle.addAction(tool_action)
            self.tool_actions.append(tool_action)

    def create_toolbar(self):
        toolbar_commands = self._engine.get_setting("toolbar_commands", [])
        if not toolbar_commands:
            return
        self.toolbar_handle.clear()
        for cmd_name in toolbar_commands:
            if cmd_name in self._engine.commands:
                self.add_shotgun_action(cmd_name, self._engine.commands[cmd_name])
        self.add_tool_actions()
        self.add_plugin_actions()
