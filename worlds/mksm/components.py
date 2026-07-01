import subprocess
import sys

from worlds.LauncherComponents import Component, Type, components, icon_paths, launch

from Utils import local_path


# def launch_client(*args: str) -> None:
#     # Spawn a real OS subprocess (instead of routing through LauncherComponents.launch(),
#     # which would run this in-process via multiprocessing with no console attached).
#     # CREATE_NEW_CONSOLE gives us an actual visible window on Windows.
#     creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
#     subprocess.Popen(
#         [sys.executable, "-m", "worlds.mksm.MKSMClient", *args],
#         cwd=local_path(),
#         creationflags=creationflags,
#     )


def run_client(*args: str) -> None:
    """
    Launch the Mortal Kombat: Shaolin Monks client.

    :param *args: Variable length argument list passed to the client.
    """
    print("Running The Mortal Kombat: Shaolin Monks Client")
    from .MKSMClient import launch as main

    launch(main, name="MKSMClient", args=args)


components.append(
    Component(
        "MKSM Client",
        func=run_client,
        game_name="Mortal Kombat: Shaolin Monks",
        icon="Mortal Kombat: Shaolin Monks",
        component_type=Type.CLIENT,
        supports_uri=True,
    )
)

icon_paths["Mortal Kombat: Shaolin Monks"] = "ap:worlds.mksm/assets/icon.png"
