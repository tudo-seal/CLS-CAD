from flask_restx import Namespace, fields


class UserDto:

    api = Namespace("user", description="User related operations.")
    user = api.model(
        "User object",
        {
            "name": fields.String,
            "username": fields.String,
            "role_id": fields.Integer,
        },
    )

    data_resp = api.model(
        "User Data Response",
        {
            "status": fields.Boolean,
            "message": fields.String,
            "user": fields.Nested(user),
        },
    )
