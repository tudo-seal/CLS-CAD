from flask import current_app

from app import db
from app.models.schemas import RepositorySchema
from app.utils import err_resp, message, internal_err_resp
from app.models.repository import Repository
repository_schema = RepositorySchema()

class RepositoryService:
    @staticmethod
    def get_repository_data(repositoryname):
        """ Get Repository data by Repositoryname """
        if not (repository := Repository.query.filter_by(repositoryname=repositoryname).first()):
            return err_resp("Repository not found!", "Repository_404", 404)

        from .utils import load_data

        try:
            repository_data = load_data(Repository)

            resp = message(True, "Repository data sent")
            resp["Repository"] = repository_data
            return resp, 200

        except Exception as error:
            current_app.logger.error(error)
            return internal_err_resp()

    @staticmethod
    def upload(data,user_id):
        # Assign vars

        ## Required values
        name = data["name"]
        repositoryname = data["repositoryname"]
        content = data["content"]

        ## Optional
        description = data.get("description")


        try:
            new_repo = Repository(
                repositoryname=repositoryname,
                name=name,
                description=description,
                content=content,
                user_id=user_id
            )

            db.session.add(new_repo)
            db.session.flush()

            # Load the new user's info
            repo_info = repository_schema.dump(new_repo)
            # Commit changes to DB
            db.session.commit()

            resp = message(True, "Repo has been uploaded.")
            resp["repository"] = repo_info

            return resp, 200

        except Exception as error:
            current_app.logger.error(error)
            return internal_err_resp()
