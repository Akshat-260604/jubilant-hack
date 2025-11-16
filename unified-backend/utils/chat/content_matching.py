import re
import pandas as pd
import unicodedata
from fuzzywuzzy import fuzz

def parse_chunks(revamped_context):
    """
    Parse document chunks from a formatted context string.

    Args:
        revamped_context (str): A string containing document chunks in the format
            "**Document: document_name | PAGE_number**\ntext content"

    Returns:
        pandas.DataFrame: A DataFrame containing parsed chunks with columns:
            - document_name (str): Name of the document
            - page_number (int): Page number in the document
            - retrieved_text (str): The extracted text content
    """
    
    chunks = []
    
   
    chunk_splits = re.split(r'\*\*Document:\s+', revamped_context)
    
    for chunk in chunk_splits:
        if not chunk.strip():
            continue
        match = re.match(r'([\w\-\.]+)\s+\|\s+PAGE_(\d+)\*\*\n+(.*)', chunk, re.DOTALL)
        if match:
            document_name = match.group(1).strip()
            page_num = int(match.group(2))
            retrieved_text = match.group(3).strip()
            chunks.append({
                'document_name': document_name,
                'page_number': page_num,
                'retrieved_text': retrieved_text
            })

    return pd.DataFrame(chunks)

def clean_text(text: str) -> str:
    """
    Comprehensive text cleaning function to remove or replace problematic characters.
 
    Args:
        text (str): The input text string to be cleaned

    Returns:
        str: Cleaned text with problematic characters removed/replaced and 
             normalized whitespace
    """
    if not text:
        return ""
 
    try:
        
        text = unicodedata.normalize('NFKD', text)
 
        
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)
 
        
        replacements = {
            '�': '',        
            '©': '',        
            '®': '',        
            '™': '',       
            '\u200b': '',   
            '\ufeff': '',   
            '\u200e': '',   
            '\u200f': '',  
            '\u202a': '',   
            '\u202b': '',   
            '\u202c': '',   
            '\u202d': '',   
            '\u202e': '',  
        }
 
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
 
    
        text = ''.join(c for c in text if (c.isprintable() and ord(c) < 65536))
 

        text = re.sub(r'\s+', ' ', text)
 
        return text
 
    except Exception as e:
        return ''.join(c for c in text if ord(c) < 128)



def match_chunks_with_df(chunks_df, content_df, fallback_threshold=0.8):
    """
    Match text chunks against content in a DataFrame using various matching strategies.

    Args:
        chunks_df (pandas.DataFrame): DataFrame containing chunks to match with columns:
            - page_number (int): Page number
            - retrieved_text (str): Text content to match
        content_df (pandas.DataFrame): DataFrame containing content to match against with columns:
            - page_number (int): Page number
            - line_number (int): Line number
            - content (str): Text content
            - coordinates (optional): Coordinates for the text
        fallback_threshold (float, optional): Minimum similarity threshold for fuzzy matching.
            Defaults to 0.8.

    Returns:
        pandas.DataFrame: DataFrame containing matched content with columns:
            - page_number (int): Page number of the match
            - line_number (int): Line number of the match
            - original_content (str): Original matched text
            - matched_content (str): Cleaned matched text
            - match_percentage (float): Match confidence score (0-100)
            - coordinates (optional): Coordinates of the matched text
    """
    results = []
    content_df.columns = content_df.columns.str.strip().str.lower().str.replace(" ", "_")
 
    for _, chunk_row in chunks_df.iterrows():
        chunk_page = int(chunk_row['page_number'])
        chunk_text = chunk_row['retrieved_text'].strip()
        chunk_text_lower = chunk_text.lower()
        chunk_words = chunk_text.split()
        expected_word_count = len(chunk_words)
        highlighted_word_count = 0
 
        page_filtered = content_df[content_df['page_number'] == chunk_page]
        matched_lines = []
        already_matched_indices = set()
 
        # Raw match
        for idx, content_row in page_filtered.iterrows():
            line_num = content_row['line_number']
            content_text = content_row['content'].strip()
            coordinates = content_row.get('coordinates', None)
 
            if not content_text:
                continue
 
            if content_text in chunk_text:
                highlighted_word_count += len(content_text.split())
                matched_lines.append({
                    'page_number': chunk_page,
                    'line_number': line_num,
                    'original_content': content_text,
                    'matched_content': content_text,
                    'match_percentage': 100,
                    'coordinates': coordinates
                })
                already_matched_indices.add(idx)
 
        coverage = highlighted_word_count / expected_word_count if expected_word_count else 1
 
        
        if coverage < 1.0:
            for idx, content_row in page_filtered.iterrows():
                if idx in already_matched_indices:
                    continue
 
                line_num = content_row['line_number']
                raw_text = content_row['content'].strip()
                cleaned_text = clean_text(raw_text)
                coordinates = content_row.get('coordinates', None)
 
                if not cleaned_text:
                    continue
 
                if cleaned_text in chunk_text:
                    highlighted_word_count += len(cleaned_text.split())
                    matched_lines.append({
                        'page_number': chunk_page,
                        'line_number': line_num,
                        'original_content': raw_text,
                        'matched_content': cleaned_text,
                        'match_percentage': 100,
                        'coordinates': coordinates
                    })
                    already_matched_indices.add(idx)
                else:
                    
                    score = fuzz.partial_ratio(cleaned_text.lower(), chunk_text_lower)
                    if score >= 90:
                        highlighted_word_count += len(cleaned_text.split())
                        matched_lines.append({
                            'page_number': chunk_page,
                            'line_number': line_num,
                            'original_content': raw_text,
                            'matched_content': cleaned_text,
                            'match_percentage': score,
                            'coordinates': coordinates
                        })
                        already_matched_indices.add(idx)
  
        results.extend(matched_lines)
 
    return pd.DataFrame(results)