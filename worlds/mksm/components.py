import subprocess
import sys

from worlds.LauncherComponents import Component, Type, components

from Utils import local_path


def launch_client(*args: str) -> None:
    # Spawn a real OS subprocess (instead of routing through LauncherComponents.launch(),
    # which would run this in-process via multiprocessing with no console attached).
    # CREATE_NEW_CONSOLE gives us an actual visible window on Windows.
    creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    subprocess.Popen(
        [sys.executable, "-m", "worlds.mksm.MKSMClient", *args],
        cwd=local_path(),
        creationflags=creationflags,
    )


components.append(
    Component(
        "MKSM Client",
        func=launch_client,
        game_name="Mortal Kombat: Shaolin Monks",
        component_type=Type.CLIENT,
        supports_uri=True,
    )
)
