from flask_restx import Api
from flask import Blueprint

from .user.controller import api as user_ns
from .repository.controller import api as repo_ns

# Import controller APIs as namespaces.
api_bp = Blueprint("api", __name__)

authorizations = {"apiKey": {"type": "apiKey", "in": "header", "name": "Authorization",'description': "Type in the *'Value'* input box below: **'Bearer &lt;JWT&gt;'**, where JWT is the token"}}

api = Api(api_bp, title="API", description="Main routes.", authorizations=authorizations, security='apiKey')

# API namespaces
api.add_namespace(user_ns)
api.add_namespace(repo_ns)
