from configs.config import QdrantSettings
from qdrant_client import QdrantClient

# Setup the qdrant client
qdrant_settings = QdrantSettings()
current_qdrant_client = QdrantClient(qdrant_settings.QDRANT_HOST_URL,timeout=300)
# send a heartbeat to the qdrant client to check if the container is up or not
try:
    print('Sending heartbeat to Qdrant Client...')
    current_qdrant_client.get_collections()
    print('Qdrant Client is up and running!')
except Exception as e:
    print(f'''
      
##################################

               __
              /._)
     _.----._/ /
    /         /
 __/ (  | (  |
/__.-'|_|--|_|

      
Could not connect to Qdrant Client. Make sure that the corresponding container is up and running. (Error: {e})
      
      
##################################''')