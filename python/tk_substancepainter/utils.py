import sgtk
import os
import sys

from sgtk.platform.qt import QtGui, QtCore
import substance_painter

import substancepainter_initialize.shelf


def get_templates(shelf_names=None):
    """
    Return a list of project templates for the given list of shelf names (or all 
    shelves if None).

    :param shelf_names: [description], defaults to None
    :type shelf_names: [type], optional
    :return: [description]
    :rtype: [type]
    """
    # NOTE: This is here just so SGTK apps can use the engine as the source of 
    # truth, even though this just delegates to the substancepainter_initialize 
    # package.
    return substancepainter_initialize.shelf.get_templates(shelf_names=shelf_names)


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
