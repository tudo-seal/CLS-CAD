# Model Schemas
from app import ma


class UserSchema(ma.Schema):
    class Meta:
        # Fields to expose, add more if needed.
        fields = ("name", "username", "role_id")


class RepositorySchema(ma.Schema):
    class Meta:
        # Fields to expose, add more if needed.
        fields = ("repositoryname","name", "content","description")
