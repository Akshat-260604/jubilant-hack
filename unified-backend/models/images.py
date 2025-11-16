
from pydantic import BaseModel
from services.document_db import get_database
from services.document_encoder import DocumentEncoder
from services.document_db import get_database


class ImageModel(BaseModel):
    id: str
    document_id: str


class ImageRepository:
    def __init__(self, database):
        self.collection = database['images']

    async def add_new_image(self,image_data:ImageModel):
        image_data_dict = image_data.model_dump(by_alias=True)
        result = await self.collection.insert_one(image_data_dict)
        return str(result.inserted_id)


    async def get_image_by_document_id(self,document_id:str):
        print("into image")
        images_cursor = self.collection.find({"document_id": document_id}, {"_id": 0})
        images = await images_cursor.to_list(length=None)
        return [image["id"] for image in images]


db=get_database()
image_repo=ImageRepository(db)