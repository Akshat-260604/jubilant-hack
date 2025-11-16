import base64
import json
import re
from datetime import datetime
import pytz

class DocumentEncoder:
    """Class for encoding and decoding document identifiers."""
    
    @staticmethod
    def encode_document_id(userId: str, document_name: str) -> str:
        """Generates a unique encoded string using user ID, document name, and current timestamp in Madrid timezone."""
        # remove.pdf from document name if present
        document_name = document_name.replace(".pdf", "")
        madrid_tz = pytz.timezone("Europe/Madrid")
        timestamp = datetime.now(madrid_tz).isoformat()
        data = json.dumps({"userId": userId, "document_name": document_name, "timestamp": timestamp})
        encoded_bytes = base64.b64encode(data.encode('utf-8'))
        return encoded_bytes.decode('utf-8')
        
    @staticmethod
    def decode_document_id(encoded_string: str):
        """Decodes the encoded string and retrieves user ID, document name, and upload timestamp."""
        decoded_bytes = base64.b64decode(encoded_string.encode('utf-8'))
        data = json.loads(decoded_bytes.decode('utf-8'))
        userId = data["userId"]
        document_name = data["document_name"]
        upload_timestamp = data["timestamp"]
        return userId, document_name, upload_timestamp
    
    @staticmethod
    def get_thumbnail_image_id(encoded_string: str):
        """Generated a thumbnail image id based on the given encoded string."""
        return f'{encoded_string}_thumb'
    
    @staticmethod
    def get_thumbnail_image_file_key(document_id: str):
        """Retrieves the thumbnail image file key in S3 from the thumbnail image id."""
        # DB/USERS/john_doe/doc_preview_images/john_ka_document/Page 1.png
        userId, document_name, upload_timestamp = DocumentEncoder.decode_document_id(document_id)
        return f'DB/USERS/{userId}/doc_preview_images/{document_name}/Page 1.png'

    @staticmethod
    def get_original_document_file_key(encoded_string: str):
        """Retrieves the original document path from the encoded string."""
        userId, document_name, _ = DocumentEncoder.decode_document_id(encoded_string)
        S3_KEY = f'DB/USERS/{userId}/docs/{document_name}.pdf'
        return S3_KEY
    
    @staticmethod
    def get_preview_images_folder_key(encoded_string: str):
        """Retrieves the preview images of the document folder path from the encoded string."""
        userId, document_name, _ = DocumentEncoder.decode_document_id(encoded_string)
        S3_KEY = f'DB/USERS/{userId}/doc_preview_images/{document_name}/'
        return S3_KEY
    
    @staticmethod
    def get_preview_images_file_key(encoded_string: str, page_number: int):
        """Retrieves the key of a specific page number's preview page."""
        userId, document_name, _ = DocumentEncoder.decode_document_id(encoded_string)
        S3_KEY = f'DB/USERS/{userId}/doc_preview_images/{document_name}/Page {page_number}.png'
        return S3_KEY

    @staticmethod
    def get_table_images_folder_key(encoded_string: str):
        """Retrieves the table images folder path from the encoded string."""
        userId, document_name, _ = DocumentEncoder.decode_document_id(encoded_string)
        S3_KEY = f'DB/USERS/{userId}/docs_tables/{document_name}/'
        return S3_KEY
    
    @staticmethod
    def get_extracted_table_image_file_key(table_image_id: str):
        """Retrieves the table image file key in S3 from the table image id."""
        # DB/USERS/john_doe/docs_tables/john_ka_document/Page 2 Table 1.png
        pattern = r"(.+)_PN(\d+)_TN(\d+)"
        match = re.match(pattern, table_image_id)
        if match:
            document_id, page_number, table_number = match.groups()
            userId, document_name, _ = DocumentEncoder.decode_document_id(document_id)
            S3_KEY = f'DB/USERS/{userId}/docs_tables/{document_name}/Page {page_number} Table {table_number}.png'
            return S3_KEY
        else:
            return None # indicate an error for invalid table image id
 
    @staticmethod
    def get_document_outline_source_images_folder_key(encoded_string: str):
        """Retrieves the document outline source images folder path from the encoded string."""
        userId, document_name, _ = DocumentEncoder.decode_document_id(encoded_string)
        S3_KEY = f'DB/USERS/{userId}/document_outline_sources/{document_name}/'
        return S3_KEY
    
    @staticmethod
    def get_document_outline_source_image_file_key(document_outline_source_image_id: str):
        """Retrieves the document outline source image key for the given document outline source image id."""
        match = re.match(r"^(.*)_PN(\d+)_DOSI$", document_outline_source_image_id)
        if match:
            document_id = match.group(1)
            page_number = int(match.group(2))
            userId, document_name, _ = DocumentEncoder.decode_document_id(document_id)
            S3_KEY = f'DB/USERS/{userId}/document_outline_sources/{document_name}/Page_{page_number}.png'
            return S3_KEY
        else:
            return None # indicate an error for invalid table image id
        
    @staticmethod
    def get_highlight_helper_table_file_key(encoded_string: str):
        """Retrieves the document outline source image key for the given document outline source image id."""
        userId, document_name, _ = DocumentEncoder.decode_document_id(encoded_string)
        S3_KEY = f'DB/USERS/{userId}/highlight_helper_tables/{document_name}.csv'
        return S3_KEY


if __name__ == '__main__':
    id = 'eyJ1c2VySWQiOiAidHQzIiwgImRvY3VtZW50X25hbWUiOiAiQVRoZXJhcGV1dGljcyBDYXRlZ29yaWVzIC0gUmVzcGlyYXRvcnkgU2VjdGlvbiAtIE9jdG9iZXIgMjAyNCIsICJ0aW1lc3RhbXAiOiAiMjAyNS0wNC0wN1QyMjowODozOC42NTU2ODErMDI6MDAifQ=='
    output = DocumentEncoder.decode_document_id(id)
    print(output)