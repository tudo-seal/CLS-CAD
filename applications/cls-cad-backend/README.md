<kbd><img src="https://github.com/tudo-seal/CLS-CAD-BACKEND/raw/main/resources/vectors/clscps.svg" width="256" height="256" style="border-radius:50%"></kbd>

---

[![Generic badge](https://img.shields.io/badge/python-3.10%20|%203.11-informational.svg)](https://shields.io/)
[![GitHub license](https://img.shields.io/github/license/tudo-seal/CLS-CAD-BACKEND)](https://github.com/tudo-seal/CLS-CAD-BACKEND/blob/main/LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7970609.svg)](https://doi.org/10.5281/zenodo.7970609)

<!---[![Issues](https://img.shields.io/github/issues/tudo-seal/CLS-CAD)](https://github.com/tudo-seal/CLS-CAD/issues)-->

---

A backend application that utilizes combinatory logic to synthesize complete cyber-physical systems, i.e. IoT devices,
robotic systems, etc. This is the backend for [CLS-CAD](https://github.com/tudo-seal/CLS-CAD).

The software version and data-set shown in the paper submitted for the ASE 2023 Tool Demonstration Track can be obtained at [Zenodo](https://doi.org/10.5281/zenodo.7970609).

# Installation

---

In the following, the steps to set up CLS-CAD-BACKEND are given.

## Prerequisites

The backend needs a MongoDB database to function.
Please either:

- Create a free account and create a database with credentials (https://www.mongodb.com/cloud/atlas/register)
- Install MongoDB locally (https://www.mongodb.com/try/download/community)

The project is intended to be set up with Poetry.
Please install Poetry. (https://python-poetry.org/docs/#installing-with-the-official-installer)

## Set Up

To install the project:

- `cd` into the project directory.
- Run `poetry install`.
- If using a hosted MongoDB database, copy `.env.template` to `.env` and fill out information.
- If using locally installed MongoDB, change the `connection url` in `cls_cad_backend/database/commands.py` to `"mongodb://localhost/?retryWrites=true&w=majority"`.

# Running

---

To run the project:

- `cd` into the project directory.
- Run `poetry run start`.
