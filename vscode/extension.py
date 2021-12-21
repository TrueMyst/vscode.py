import sys
import json
import asyncio
import websockets
from typing import Any, Callable, Optional

from vscode.compiler import build
from vscode.utils import *

__all__ = (
    'Extension',
    'Command'
)

class Extension:
    """
    Represents a vscode extension.
    """

    def __init__(self, name: str) -> None:
        self.name = name.lower().replace(" ", "-")
        self.display_name = name


        self.commands = []
        self.events = {}
        self.default_category = None
        self.keybindings = []

    def __repr__(self):
        return f"<vscode.Extension {self.name}>"  

    def register_command(
        self,
        func: Callable[..., Any],
        name: Optional[str] = None,
        title: Optional[str] = None,
        category: Optional[str] = None,
        keybind: Optional[str] = None,
        when: Optional[str] = None,
    ) -> None:
        """
        Register a command.
        This is usually not called, instead the command() shortcut decorators should be used instead.
        Args:
            func: The function to register as a command.
            name: The internal name of the command.
            title: The title of the command. This is shown in the command palette.
            category: The category that this command belongs to.
                Default categories set by Extensions will be overriden if this is not None.
                False should be passed in order to override a default category.
            keybind: The keybind for this command.
            when: A condition for when keybinds should be functional.
        """
        name = func.__name__ if name is None else name
        category = self.default_category if category is None else category
        command = Command(name, func, title, category, keybind, when)
        if keybind:
            self.register_keybind(command)
        self.commands.append(command)

    def command(
        self,
        name: Optional[str] = None,
        title: Optional[str] = None,
        category: Optional[str] = None,
        keybind: Optional[str] = None,
        when: Optional[str] = None,
    ):
        """
        A decorator for registering commands.
        Args:
            name: The internal name of the command.
            title: The title of the command. This is shown in the command palette.
            category: The category that this command belongs to.
                Default categories set by Extensions will be overriden if this is not None.
                False should be passed in order to override a default category.
            keybind: The keybind for this command.
            when: A condition for when keybinds should be functional.
        """

        def decorator(func):
            self.register_command(func, name, title, category, keybind, when)
            return func

        return decorator

    def register_keybind(self, command: "Command") -> None:
        """
        A method called internally to register a keybind.
        """
        keybind = {"command": command.extension(self.name), "key": command.keybind}
        if command.when:
            keybind.update({"when": command.when})
        self.keybindings.append(keybind)

    def run(self):
        
        if len(sys.argv) > 1:
            async def main():
                async with websockets.serve(self.receive_websockets, "localhost", 8765):
                    await asyncio.Future()  # run forever

            asyncio.run(main())
        else:
            build(self)      

    async def receive_websockets(self, websocket, path):
        while True:
            data = await websocket.recv()
            name = json.loads(data).get('name')
            print(f"<<< {name}")

            greeting = f"Hello {name}!"

            await websocket.send(greeting)
            print(f">>> {greeting}")

class Command:
    """
    A class that implements the protocol for commands that can be used via the command palette.
    These should not be created manually, instead they should be created via the
    decorator or functional interface.
    """

    def __init__(
        self,
        name: str,
        func: Callable,
        title: Optional[str] = None,
        category: Optional[str] = None,
        keybind: Optional[str] = None,
        when: Optional[str] = None,
    ):
        """
        Initialize a command.
        Args:
            name: The internal name of the command.
            func: The function to register as a command.
            title: The title of the command. This is shown in the command palette.
            category: The category that this command belongs to.
            keybind: The keybind for this command.
            when: A condition for when keybinds should be functional.
        """

        self.name = snake_case_to_camel_case(name)
        self.title = snake_case_to_title_case(name)

        if not asyncio.iscoroutinefunction(func):
            raise TypeError("Callback must be a coroutine.")

        self.func = func
        self.func_name = self.func.__name__
        self.category = None if category is False else category
        self.keybind = keybind.upper() if keybind is not None else None
        self.when = python_condition_to_js_condition(when) 

    def __repr__(self):
        return f"<vscode.Command {self.name}>"

    def extension(self, ext_name: str) -> str:
        """
        The string representation for an extension.
        """
        return f"{ext_name}.{self.name}"
