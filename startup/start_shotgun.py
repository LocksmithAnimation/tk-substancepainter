# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
This file is loaded automatically by SubstancePainter at startup
It sets up the Toolkit context and prepares the tk-substancepainter engine.
"""

import os
import sys
import traceback

import substancepainter_initialize.shelf

__author__ = "Diego Garcia Huerta"
__email__ = "diegogh2000@gmail.com"


def display_error(logger, msg):
    logger.error(f"Shotgun Error | SubstancePainter engine | {msg}")
    print(f"Shotgun Error | SubstancePainter engine | {msg}")


def display_warning(logger, msg):
    logger.warning(f"Shotgun Warning | SubstancePainter engine | {msg}")
    print(f"Shotgun Warning | SubstancePainter engine | {msg}")


def display_info(logger, msg):
    logger.info(f"Shotgun Info | SubstancePainter engine | {msg}")
    print(f"Shotgun Info | SubstancePainter engine | {msg}")


def start_toolkit_classic():
    """
    Parse enviornment variables for an engine name and
    serialized Context to use to startup Toolkit and
    the tk-substancepainter engine and environment.
    """
    import sgtk

    logger = sgtk.LogManager.get_logger(__name__)

    logger.debug("Launching toolkit in classic mode.")

    # Get the name of the engine to start from the environement
    env_engine = os.environ.get("SGTK_ENGINE")
    if not env_engine:
        msg = "Shotgun: Missing required environment variable SGTK_ENGINE."
        display_error(logger, msg)
        return

    # Get the context load from the environment.
    env_context = os.environ.get("SGTK_CONTEXT")
    if not env_context:
        msg = "Shotgun: Missing required environment variable SGTK_CONTEXT."
        display_error(logger, msg)
        return
    try:
        # Deserialize the environment context
        context = sgtk.context.deserialize(env_context)
    except Exception as e:
        msg = (
            "Shotgun: Could not create context! Shotgun Pipeline Toolkit"
            f" will be disabled. Details: {e}"
        )
        etype, value, tb = sys.exc_info()
        msg += "".join(traceback.format_exception(etype, value, tb))
        display_error(logger, msg)
        return

    substancepainter_initialize.shelf.register_pipeline_shelf()

    try:
        # Start up the toolkit engine from the environment data
        logger.debug(
            f"Launching engine instance '{env_engine}' for context {env_context}"
        )
        sgtk.platform.start_engine(env_engine, context.sgtk, context)
        logger.debug(f"Current engine '{sgtk.platform.current_engine()}'")

    except Exception as e:
        msg = f"Shotgun: Could not start engine. Details: {e}"
        etype, value, tb = sys.exc_info()
        msg += "".join(traceback.format_exception(etype, value, tb))
        display_error(logger, msg)
        return


def start_toolkit():
    """
    Import Toolkit and start up a tk-substancepainter engine based on
    environment variables.
    """

    # Verify sgtk can be loaded.
    try:
        import sgtk
    except Exception as e:
        msg = f"Shotgun: Could not import sgtk! Disabling for now: {e}"
        print(msg)
        return

    # start up toolkit logging to file
    sgtk.LogManager().initialize_base_file_handler("tk-substancepainter")

    # Rely on the classic boostrapping method
    start_toolkit_classic()

    # Check if a file was specified to open and open it.
    file_to_open = os.environ.get("SGTK_FILE_TO_OPEN")
    if file_to_open:
        msg = f"Shotgun: Opening '{file_to_open}'..."
        # TODO load a project if specified
        # .App.loadProject(file_to_open)

    # Clean up temp env variables.
    del_vars = [
        "SGTK_ENGINE",
        "SGTK_CONTEXT",
        "SGTK_FILE_TO_OPEN",
    ]
    for var in del_vars:
        if var in os.environ:
            del os.environ[var]


def start_plugin():
    """This method is called when the plugin is started."""
    start_toolkit()


def close_plugin():
    import sgtk

    engine = sgtk.platform.current_engine()
    if engine:
        engine.destroy()


if __name__ == "__main__":
    start_plugin()
