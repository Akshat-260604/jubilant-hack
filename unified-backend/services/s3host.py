import os
import re
import aioboto3
from mimetypes import guess_type
from botocore.config import Config
from botocore.exceptions import ClientError
from utils.document_handling.logger import log
from services.document_encoder import DocumentEncoder
import pandas as pd
import io
from configs.config import aws_settings

class AsyncS3Host:
    def __init__(self):
        my_config_global = Config(
            region_name="us-east-1",
            signature_version="s3v4",
        )

        # Create a session using AWS credentials from config or environment variables
        self.session = aioboto3.Session(
            aws_access_key_id=aws_settings.access_key or os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=aws_settings.secret_key or os.getenv("AWS_SECRET_ACCESS_KEY", "")
        )
            
        self.config = my_config_global
        # Use environment variable for bucket name with a fallback
        self.bucket_name = os.getenv("BUCKET_NAME", "pharma-ai-suite")

    async def _upload_to_s3(self, key, data, content_type=None):
        try:
            async with self.session.client("s3", config=self.config) as s3_client:
                await s3_client.put_object(Bucket=self.bucket_name, Key=key, Body=data, ContentType=content_type)
            log(f"Data uploaded to S3 with key: {key}")
        except Exception as e:
            log(f"Error uploading to S3: {e}")
            raise e

    async def get_presigned_upload_url(self, complete_pdf_name: str, userId: str, expire_in_n_seconds: int =18000):
        try:
            key = f"DB/USERS/{userId}/docs/{complete_pdf_name}"
            key= await self.get_available_file_key(key)
            
            final_file_name = key.rsplit("/", 1)[-1]
            document_id = DocumentEncoder.encode_document_id(userId=userId, document_name=final_file_name)

            async with self.session.client("s3", config=self.config) as s3_client:
                presigned_url = await s3_client.generate_presigned_url(
                    "put_object",
                    Params={"Bucket": self.bucket_name, "Key": key},
                    ExpiresIn=expire_in_n_seconds,  # default is 1 hour expiration
                )
            return presigned_url, document_id

        except ClientError as e:
            log(f"Error getting presigned upload URL: {e}")
            raise e

    async def get_presigned_view_url(self, key: str, expire_in_n_seconds: int = 18000):
        try:
            async with self.session.client("s3", config=self.config) as s3_client:
                presigned_url = await s3_client.generate_presigned_url(
                    "get_object", 
                    Params={"Bucket": self.bucket_name, "Key": key}, 
                    ExpiresIn=expire_in_n_seconds
                )
            print("key obtained: ", key)
            return presigned_url
        except ClientError as e:
            log(f"Error generating presigned view URL: {e}")
            raise e

    async def check_document_exists(self, document_id: str) -> bool:
        """
        Check if a document exists in S3
        """
        try:
            # Extract complete_pdf_name from document_id (remove userId prefix)
            key = DocumentEncoder.get_original_document_file_key(document_id)
            log(f"Looking for key {key} in the bucket to process the document with document_id {document_id}")

            try:
                # Try to get object head to check if file exists
                async with self.session.client("s3", config=self.config) as s3_client:
                    await s3_client.head_object(Bucket=self.bucket_name, Key=key)
                return True
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    return False
                else:
                    raise e

        except Exception as e:
            log(f"Error checking document existence: {e}")
            raise e
    async def get_available_file_key(self, key: str) -> str:
        """
        Get an available file key in S3 by appending a counter (_1, _2, ...) 
        if the original key already exists. Does NOT strip existing suffixes.
        """
        try:
            base_path, file_name = key.rsplit("/", 1)
            name, extension = os.path.splitext(file_name)

            counter = 0
            new_key = key

            async with self.session.client("s3", config=self.config) as s3_client:
                while True:
                    try:
                        await s3_client.head_object(Bucket=self.bucket_name, Key=new_key)
                        # If exists, increment and try again
                        counter += 1
                        new_file_name = f"{name}_{counter}{extension}"
                        new_key = f"{base_path}/{new_file_name}"
                    except ClientError as e:
                        if e.response["Error"]["Code"] == "404":
                            return new_key
                        else:
                            raise e

        except Exception as e:
            log(f"Error getting available file name: {e}")
            raise e

    async def get_document(self, document_id: str):
        """
        Get document from S3 and return its contents as bytes along with fileName
        Returns:
            Tuple[bytes, str]: (file_content, fileName)
        """
        try:
            # get the key of the document's path in s3
            document_key_in_s3 = DocumentEncoder.get_original_document_file_key(document_id)

            # get the document name from the encode
            userId, document_name, upload_timestamp = DocumentEncoder.decode_document_id(document_id)

            # Get the object from S3
            async with self.session.client("s3", config=self.config) as s3_client:
                response = await s3_client.get_object(Bucket=self.bucket_name, Key=document_key_in_s3)
                # Read the data from the response
                pdf_data = await response["Body"].read()

            # Return both the content and fileName
            return pdf_data, f"{document_name}"

        except ClientError as e:
            log(f"Error retrieving document from S3: {e}")
            raise e
        except Exception as e:
            log(f"Error processing document data: {e}")
            raise e

    async def save_to_s3(self, file_data, key):
        """
        Saves a file to S3 bucket.

        Args:
            file_data: The data to be uploaded.
            key: The S3 key where the file will be stored.

        Returns:
            None
        """
        file_type, _ = guess_type(key)
        await self._upload_to_s3(key, file_data, content_type=file_type)

    async def delete_from_s3(self, key: str):
        """
        Deletes a file or all files within a folder (including subfolders) from S3.

        Args:
            key (str): The S3 key of the file or folder to delete.
        """
        try:
            async with self.session.client("s3", config=self.config) as s3_client:
                if key.endswith("/"):  # If it's a folder
                    objects_to_delete = []
                    continuation_token = None

                    # Paginate through all objects to ensure all nested objects are retrieved
                    while True:
                        list_kwargs = {"Bucket": self.bucket_name, "Prefix": key}
                        if continuation_token:
                            list_kwargs["ContinuationToken"] = continuation_token

                        response = await s3_client.list_objects_v2(**list_kwargs)

                        if "Contents" in response:
                            objects_to_delete.extend([{"Key": obj["Key"]} for obj in response["Contents"]])

                        # If there are more objects, continue listing
                        continuation_token = response.get("NextContinuationToken")
                        if not continuation_token:
                            break

                    if objects_to_delete:
                        await s3_client.delete_objects(Bucket=self.bucket_name, Delete={"Objects": objects_to_delete})
                        log(f"Deleted all objects in folder and subfolders: {key}")
                    else:
                        log(f"No objects found in folder: {key}")

                else:  # If it's a file
                    await s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                    log(f"Deleted file: {key}")

        except ClientError as e:
            log(f"Error deleting from S3: {e}")
            raise e
        except Exception as e:
            log(f"Unexpected error deleting from S3: {e}")
            raise e
        
    async def load_csv_as_dataframe(self, key: str) -> pd.DataFrame:
        """
        Downloads a CSV file from S3 and loads it into a pandas DataFrame.

        Args:
            key (str): The S3 key of the CSV file.

        Returns:
            pd.DataFrame: DataFrame loaded from the CSV file.
        """
        try:
            async with self.session.client("s3", config=self.config) as s3_client:
                response = await s3_client.get_object(Bucket=self.bucket_name, Key=key)
                csv_bytes = await response["Body"].read()
                csv_str = csv_bytes.decode("utf-8")
                df = pd.read_csv(io.StringIO(csv_str))
                return df
        except ClientError as e:
            log(f"Error loading CSV from S3: {e}")
            raise e
        except Exception as e:
            log(f"Unexpected error loading CSV from S3: {e}")
            raise e



# Create an instance of the async client
current_s3_client = AsyncS3Host()