from flask_restx import Namespace, fields


class RepositoryDto:

    api = Namespace("repository", description="Repository related operations.")
    Repository = api.model(
        "Repository object",
        {
            "name": fields.String,
            "repositoryname": fields.String(required=True),
            "name": fields.String,
            "description": fields.String,
            "content": fields.Raw(required=True),
        },
    )

    data_resp = api.model(
        "Repository Data Response",
        {
            "status": fields.Boolean,
            "message": fields.String,
            "repository": fields.Nested(Repository),
        },
    )

    upload_resp_success = api.model(
        "Repository Upload Response",
        {
            "status": fields.Boolean,
            "message": fields.String,
            "repository": fields.Nested(Repository),
        },
    )
