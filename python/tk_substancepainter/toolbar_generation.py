from sgtk.platform.qt import QtGui, QtCore
import substance_painter


class ToolbarGenerator(object):

    def __init__(self, engine):
        self._engine = engine
        self.toolbar_handle = None
        self.toolbar_commands = engine.get_setting("toolbar_commands", [])

    def cleanup(self):
        substance_painter.ui.delete_ui_element(self.toolbar_handle)

    def create_toolbar(self):
        if not self.toolbar_commands:
            return
        self.toolbar_handle = substance_painter.ui.add_toolbar("Shotgun Toolbar", "ls_shotgun_toolbar")
        self.toolbar_handle.clear()
        for (cmd_name, cmd_details) in self._engine.commands.items():
            if cmd_name in self.toolbar_commands:
                self.create_action(cmd_name, cmd_details)

    def create_action(self, cmd_name, cmd_details):
        action = None
        if cmd_details["properties"]["icons"]["dark"]["png"]:
            icon = QtGui.QIcon(cmd_details["properties"]["icons"]["dark"]["png"])
            action = QtGui.QAction(icon, "", self.toolbar_handle)
        self.toolbar_handle.addAction(action)
        action.triggered.connect(cmd_details["callback"])
        action.setToolTip(cmd_name)
        action.setStatusTip(cmd_name)
        return action