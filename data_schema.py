from mongoengine import Document, EmbeddedDocument, StringField, EmbeddedDocumentListField, ObjectIdField 
from bson import ObjectId
class Note(EmbeddedDocument):
    id = ObjectIdField(default=ObjectId, unique=True)
    title=StringField(required=True, max_length=50)
    content=StringField(required=True)
    
class User(Document):
    name=StringField(required=True, max_length=50)
    notes=EmbeddedDocumentListField(Note)

