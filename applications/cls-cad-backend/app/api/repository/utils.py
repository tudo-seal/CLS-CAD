def load_data(Repository_db_obj):
    """ Load Repository's data

    Parameters:
    - Repository db object
    """
    from app.models.schemas import RepositorySchema

    repository_schema = RepositorySchema()

    data = repository_schema.dump(Repository_db_obj)

    return data
