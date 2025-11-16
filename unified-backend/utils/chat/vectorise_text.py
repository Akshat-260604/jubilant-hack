from numpy import array
from services.ollama_host import current_ollama_client

async def vectorise_text(text:str):
    '''
    Computes the embeddings for a given text

    Args:
        text (str): The input text for which embeddings need to be computed.

    Returns:
        numpy.ndarray: The computed embeddings as a 1D numpy array.
    '''
    response = current_ollama_client.embed_documents([text])
    embeddings = array(response).squeeze()
    return embeddings