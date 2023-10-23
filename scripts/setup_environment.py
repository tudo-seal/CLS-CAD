import subprocess
from os import path


def setup():
    subprocess.check_call(
        'mklink /J "{}" "{}"'.format(
            path.expandvars(
                r"%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\CLS-CAD"
            ),
            "applications/cls-cad-fusion-plugin",
        ),
        shell=True,
    )


if __name__ == "__main__":
    setup()
