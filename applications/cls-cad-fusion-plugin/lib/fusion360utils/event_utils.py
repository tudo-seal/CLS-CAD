import sys
from collections.abc import Callable

import adsk.core

from .general_utils import handle_error

# Global Variable to hold Event Handlers
_handlers = []


def add_handler(
    event: adsk.core.Event,
    callback: Callable,
    *,
    name: str = None,
    local_handlers: list = None
):
    """
    Adds an event handler to the specified event.

    Args:
      event: The event object you want to connect a handler to
      callback: The function that will handle the event
      name: A name to use in logging errors associated with this event
      Otherwise: the name of the event object is used
      must: be specified by its keyword
      local_handlers: A list of handlers you manage that is used to maintain
      a: reference to the handlers so they aren
      This: argument must be specified by its keyword
      specified: the handler is added to a global list and can
      be: cleared using the clear_handlers function
      to: maintain your own handler list so it can be managed
      independently: for each command
      event: adsk.core.Event:
      callback: Callable: :param *:
      name: str:  (Default value = None)
      local_handlers: list:  (Default value = None)
      event: adsk.core.Event:
      callback: Callable:
      *:
      name: str:  (Default value = None)
      local_handlers: list:  (Default value = None)

    Returns:

    Args:
      event: adsk.core.Event:
      callback: Callable:
      event: adsk.core.Event:
      callback: Callable:
      *:
      name: str:  (Default value = None)
      local_handlers: list:  (Default value = None)

    Returns:

    :param event: adsk.core.Event:
    :param callback: Callable:
    :param *:
    :param name: str:  (Default value = None)
    :param local_handlers: list:  (Default value = None)
    """
    module = sys.modules[event.__module__]
    handler_type = module.__dict__[event.add.__annotations__["handler"]]
    handler = _create_handler(handler_type, callback, event, name, local_handlers)
    event.add(handler)


def clear_handlers():
    """Clears the global list of handlers."""
    global _handlers
    _handlers = []


def _create_handler(
    handler_type,
    callback: Callable,
    event: adsk.core.Event,
    name: str = None,
    local_handlers: list = None,
):
    """
    :param handler_type: param callback: Callable:
    :param event: adsk.core.Event:
    :param name: str:  (Default value = None)
    :param local_handlers: list:  (Default value = None)
    :param callback: Callable:
    """
    handler = _define_handler(handler_type, callback, name)()
    (local_handlers or _handlers).append(handler)
    return handler


def _define_handler(handler_type, callback, name: str = None):
    """
    :param handler_type: param callback:
    :param name: str:  (Default value = None)
    :param callback: param name: str:  (Default value = None)
    """
    name = name or handler_type.__name__

    class Handler(handler_type):
        """"""

        def __init__(self):
            super().__init__()

        def notify(self, args):
            """

            :param args:

            """
            try:
                callback(args)
            except:
                handle_error(name)

    return Handler
