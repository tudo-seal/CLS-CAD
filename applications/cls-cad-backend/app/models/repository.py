from datetime import datetime
from app import db, bcrypt

# Alias common DB names
Column = db.Column
Model = db.Model
relationship = db.relationship


class Repository(Model):
    """ Repository model for storing CLS repositories as JSON data """

    id = Column(db.Integer, primary_key=True)
    content = Column(db.JSON)
    repositoryname = Column(db.String(64))
    name = Column(db.String(64))
    description = Column(db.String(512))

    user_id = Column(db.Integer, db.ForeignKey("user.id"))

    def __init__(self, **kwargs):
        super(Repository, self).__init__(**kwargs)

