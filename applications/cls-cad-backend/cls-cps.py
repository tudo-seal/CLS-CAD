import os

import flask_migrate
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

##

import click
from flask_migrate import Migrate
from app import create_app, db

# Import models
from app.models.user import User, Role, Permission
from app.models.repository import Repository


app = create_app(os.getenv("FLASK_CONFIG") or "default")
migrate = Migrate(app, db)
# To avoid manually making an in memory db for every rerun, when testing we automate it
if(os.getenv("FLASK_CONFIG") == "testing"):
    with app.app_context():
        try:
            flask_migrate.init()
            flask_migrate.migrate()
        except:
            pass
        flask_migrate.upgrade()


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role, Permission=Permission, Repository=Repository)


@app.cli.command()
@click.argument("command", nargs=-1)
def execute(command):

    match command:
        case _: pass

