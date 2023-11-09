<kbd><img src="https://github.com/tudo-seal/CLS-CAD/raw/main/applications/cls-cad-fusion-plugin/resources/vectors/clscad.svg" width="256" height="256" style="border-radius:50%"></kbd>

---

[![Generic badge](https://img.shields.io/badge/python-fusion360%20|%203.10%20|%203.11-informational.svg)](https://shields.io/)
[![Supported systems](https://img.shields.io/badge/os-windows-informational.svg)](https://shields.io/)
[![GitHub license](https://img.shields.io/github/license/tudo-seal/CLS-CAD)](https://github.com/tudo-seal/CLS-CAD/blob/main/LICENSE)
![Generate Latest Release](https://github.com/tudo-seal/CLS-CAD/actions/workflows/generate-latest-release.yml/badge.svg)
[![CodeCov](https://codecov.io/gh/tudo-seal/CLS-CAD/graph/badge.svg)](https://codecov.io/gh/tudo-seal/CLS-CAD)

<!---[![Issues](https://img.shields.io/github/issues/tudo-seal/CLS-CAD)](https://github.com/tudo-seal/CLS-CAD/issues)-->

---

An add-in and matching backend that allows adding types to Joint Origins and Parts in Fusion 360, and allows requesting and assembling results by means of combinatory logic.

# Installation

To install the add-in in Fusion 360, download the [latest installer](https://github.com/tudo-seal/CLS-CAD/releases/download/latest/cls-cad-fusion-plugin.msi) and execute it.
To use the plugin, you need a running backend.
This requires [docker](https://docs.docker.com/desktop/install/windows-install/) to be installed.

After installing and starting docker, in a terminal, run:

- `docker run -d -p 8000:80 --name cls-cad-backend --pull=always ghcr.io/tudo-seal/cls-cad-backend:latest`

For subsequent usage, simply start the `cls-cad-backend` container from the containers tab in the docker desktop application.

# Getting Started

Create an [Autodesk account](https://www.autodesk.com/education/edu-software). An education license is recommended if applicable. Then, install [Fusion 360](https://manage.autodesk.com/products).
Launch Fusion 360, Sign in, and then close Fusion 360.

- Install the add-in using the [latest installer](https://github.com/tudo-seal/CLS-CAD/releases/download/latest/cls-cad-fusion-plugin.msi).
- Run the backend (using docker, as detailed in the Installation section)
- Download the [modular components for synthesizing robotic arms](https://doi.org/10.5281/zenodo.10051244) dataset.
- Launch Fusion 360 and create a new empty project. Open that project.
- Upload all .f3d files from the [modular components for synthesizing robotic arms](https://doi.org/10.5281/zenodo.10051244) to that project.
- Switch to the CLS-CAD tab in Fusion 360, and press the `Upload Taxonomy` button. Select the .taxonomy in the [modular components for synthesizing robotic arms](https://doi.org/10.5281/zenodo.10051244).
- Press the `Crawl Project` button in the CLS-CAD tab and wait for the process to complete.

That's it! You can now start requesting results.

- At the far right of the CLS-CAD tab, press the `Request Synthesis` button.
- Select the part type `Base` in the upper taxonomy.
- Hit Ok, then press the `Assemble Results` button to explore and assemble any results.

You can switch to the `Counted Types` when requesting designs to add numerical constraints and narrow down the results.

# Basic Usage

- Create taxonomies for a project by using the graphical taxonomy editors.
- Place Joint Origins.
- Type the placed Joint Origins.
- Type the parts.
- Submit the parts to the backend.
- Request synthesis.
- Explore and assemble the results.

For a short video illustrating the process, see: https://www.youtube.com/watch?v=gK00StSAxuk
