from flask import request
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

from .service import RepositoryService
from .dto import RepositoryDto
from ...models.schemas import RepositorySchema
from ...utils import validation_error

api = RepositoryDto.api
data_resp = RepositoryDto.data_resp

repository_schema = RepositorySchema()
upload_resp_success = RepositoryDto.upload_resp_success


@api.route("/<string:repositoryname>")
class RepositoryGet(Resource):
    @api.doc(
        "Get a specific Repository",
        responses={
            200: ("Repository data successfully sent", data_resp),
            404: "Repository not found!",
        },
    )
    @jwt_required()
    def get(self, repositoryname):
        """ Get a specific Repository's data by their repositoryname """
        return RepositoryService.get_Repository_data(repositoryname)

@api.route("/upload")
class RepositoryUpload(Resource):
    """ User login endpoint
    User registers then receives the user's information and access_token
    """

    repository_upload = RepositoryDto.Repository

    @api.doc(
        "Repository Upload",
        responses={
            200: ("Uploaded.", upload_resp_success),
            400: "Validations failed.",
        },
    )
    @api.expect(repository_upload, validate=True)
    @jwt_required()
    def post(self):
        """ Upload a repository, upon success owned by the logged-in user. """
        user_id = get_jwt_identity()
        upload_data = request.get_json()
        if (errors := repository_schema.validate(upload_data)) :
            return validation_error(False, errors), 400
        return RepositoryService.upload(upload_data,user_id)

