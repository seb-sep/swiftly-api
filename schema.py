from mongoengine import Document, EmbeddedDocument, StringField, EmbeddedDocumentListField 

class Note(EmbeddedDocument):
    name=StringField(required=True, max_length=50)
    content=StringField(required=True)
    
class User(Document):
    name=StringField(required=True, max_length=50)
    notes=EmbeddedDocumentListField(Note)

