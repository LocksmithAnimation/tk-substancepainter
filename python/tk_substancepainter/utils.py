import sgtk
import os
import sys

from sgtk.platform.qt import QtGui, QtCore
import substance_painter


def get_unlisted_resources(file_extension, shelf_subdir, shelf_names=None):
    resources = {}
    engine = sgtk.platform.current_engine()
    all_shelves = get_shelves()
    shelves = {}

    if (shelf_names):
        for shelf_name in shelf_names:
            shelves[shelf_name] = all_shelves[shelf_name]
    else:
        shelves = all_shelves

    for shelf_name, shelf_path in shelves.items():
        resource_dir = os.path.join(shelf_path, shelf_subdir)
        if not os.path.exists(resource_dir):
            continue
        files = os.listdir(resource_dir)

        for f in files:
            full_path = os.path.join(resource_dir, f)
            if os.path.isdir(full_path):
                continue

            if f.endswith(".{}".format(file_extension)):
                resources[f.split(".")[0]] = full_path
    return resources


def get_shelves():
    install_path = os.path.dirname(sys.executable)
    shelf_path = os.path.join(install_path, "resources", "shelf")
    shelves = {x:os.path.join(shelf_path, x) for x in os.listdir(shelf_path) if os.path.isdir(os.path.join(shelf_path, x))}
    return shelves


class CheckFilter(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() is QtCore.QEvent.Type.Close:
            self.kill_it(obj)
            return True
        return QtCore.QObject.eventFilter(self, obj, event)

    def kill_it(self, dock_widget):
        engine = sgtk.platform.current_engine()
        dock_widget.widget().close()
        substance_painter.ui.delete_ui_element(dock_widget)
        if engine and dock_widget in engine.widgets:
            engine.widgets.remove(dock_widget)
