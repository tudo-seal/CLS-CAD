<kbd><img src="https://github.com/tudo-seal/CLS-CAD/raw/main/applications/cls-cad-fusion-plugin/resources/vectors/clscad.svg" width="256" height="256" style="border-radius:50%"></kbd>

---

[![Generic badge](https://img.shields.io/badge/python-fusion360-informational.svg)](https://shields.io/)
[![Supported systems](https://img.shields.io/badge/os-windows%20|%20macOS-informational.svg)](https://shields.io/)
[![GitHub license](https://img.shields.io/github/license/tudo-seal/CLS-CAD)](https://github.com/tudo-seal/CLS-CAD/blob/main/LICENSE)

<!---[![Issues](https://img.shields.io/github/issues/tudo-seal/CLS-CAD)](https://github.com/tudo-seal/CLS-CAD/issues)-->

---

An add-in and matching backend that allows adding types to Joint Origins and Parts in Fusion 360, and allows requesting and assembling results by means of combinatory logic.

# Installation

To install the add-in in Fusion 360, download the latest installer and execute it.
To use the plugin, you need a running backend.
This requires [docker](https://docs.docker.com/desktop/install/windows-install/) to be installed.

After installing and starting docker, run:

- `docker run -d ghcr.io/tudo-seal/cls-cad-backend:latest -p 8000:80 --name cls-cad-backend --pull=always`

# Basic Usage

- Create taxonomies for a project by using the graphical taxonomy editors.
- Place Joint Origins.
- Type the placed Joint Origins.
- Type the parts.
- Submit the parts to the backend.
- Request synthesis.
- Explore and assemble the results.

For a short video illustrating the process, see: https://www.youtube.com/watch?v=gK00StSAxuk
