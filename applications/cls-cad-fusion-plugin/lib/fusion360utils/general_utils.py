import traceback

import adsk.core

app = adsk.core.Application.get()
ui = app.userInterface

# Attempt to read DEBUG flag from parent config.
try:
    from ... import config

    DEBUG = config.DEBUG
except:
    DEBUG = False


def log(
    message: str,
    level: adsk.core.LogLevels = adsk.core.LogLevels.InfoLogLevel,
    force_console: bool = False,
):
    """
    Utility function to easily handle logging in your app.

    :param message: str:
    :param level: adsk.core.LogLevels: (Default value =
        adsk.core.LogLevels.InfoLogLevel)
    :param force_console: bool: (Default value = False)
        adsk.core.LogLevels.InfoLogLevel)
    """
    # Always print to console, only seen through IDE.
    print(message)

    # Log all errors to Fusion log file.
    if level == adsk.core.LogLevels.ErrorLogLevel:
        log_type = adsk.core.LogTypes.FileLogType
        app.log(message, level, log_type)

    # If config.DEBUG is True write all log messages to the console.
    if DEBUG or force_console:
        log_type = adsk.core.LogTypes.ConsoleLogType
        app.log(message, level, log_type)


def handle_error(name: str, show_message_box: bool = False):
    """
    Utility function to simplify error handling.

    :param name: str:
    :param show_message_box: bool:  (Default value = False)
    :param If: False
    :param and: logged to the log file
    """

    log("===== Error =====", adsk.core.LogLevels.ErrorLogLevel)
    log(f"{name}\n{traceback.format_exc()}", adsk.core.LogLevels.ErrorLogLevel)

    # If desired you could show an error as a message box.
    if show_message_box:
        ui.messageBox(f"{name}\n{traceback.format_exc()}")
