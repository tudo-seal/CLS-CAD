from flask_restx import Namespace, fields


class AuthDto:
    api = Namespace("auth", description="Authenticate and receive tokens.")

    user_obj = api.model(
        "User object",
        {
            "name": fields.String,
            "username": fields.String,
            "role_id": fields.Integer,
        },
    )

    auth_login = api.model(
        "Login data",
        {
            "username": fields.String(required=True),
            "password": fields.String(required=True),
        },
    )

    auth_register = api.model(
        "Registration data",
        {
            "username": fields.String(required=True),
            # Name is optional
            "name": fields.String,
            "password": fields.String(required=True),
        },
    )

    auth_success = api.model(
        "Auth success response",
        {
            "status": fields.Boolean,
            "message": fields.String,
            "access_token": fields.String,
            "user": fields.Nested(user_obj),
        },
    )
