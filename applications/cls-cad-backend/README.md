<kbd><img src="https://github.com/tudo-seal/CLS-CPS/raw/main/resources/vectors/clscps.svg" width="256" height="256" style="border-radius:50%"></kbd>

---

A backend application that utilizes combinatory logic to synthesize complete cyber-physical systems, i.e. IoT devices,
robotic systems, etc. This is the backend for [CLS-CAD](https://github.com/tudo-seal/CLS-CAD).

# Installation

---

In the following, the steps to set up CLS-CPS are given.

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
- If using locally installed MongoDB, change the `connection url` in `cls_cps/database/commands.py` to `"mongodb://localhost/?retryWrites=true&w=majority"`.

# Running

---

To run the project:

- `cd` into the project directory.
- Run `poetry run start`.
