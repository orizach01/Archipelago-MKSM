from worlds.LauncherComponents import Component, Type, components, icon_paths, launch


def run_client(*args: str) -> None:
    """
    Launch the Mortal Kombat: Shaolin Monks client.

    :param *args: Variable length argument list passed to the client.
    """
    from .MKSMClient import launch_client as main

    launch(main, name="MKSM Client", args=args)


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
