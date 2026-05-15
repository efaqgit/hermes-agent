#!/usr/bin/env python3
"""
Medical Text Ingestion Tool for TCM Dashboard (RAG Prep)

This script allows users to ingest local text files of classical medical books
(like Ben Jing Shu Zheng 《本經疏證》) to build a local knowledge base.
It processes text files, chunks them logically by paragraphs or chapters,
and saves them into a structured JSON DB format ready for future RAG 
(Retrieval-Augmented Generation) integrations.

Usage:
  python3 ingest_medical_text.py --input /path/to/book.txt --output /path/to/db.json --book_name "本經疏證"
"""

import os
import sys
import json
import argparse
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("MedicalIngester")

def chunk_text(text: str, max_chars: int = 1000) -> List[str]:
    """
    Split text into chunks by paragraphs, attempting to keep them under max_chars.
    """
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    chunks = []
    current_chunk = ""

    for p in paragraphs:
        if len(current_chunk) + len(p) < max_chars:
            current_chunk += p + "\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = p + "\n"
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

def ingest_content(content: str, book_name: str, source: str = "upload") -> List[Dict]:
    """
    Parse string content into chunks, and return a list of structured records.
    """
    chunks = chunk_text(content)
    logger.info(f"Parsed '{book_name}' into {len(chunks)} chunks.")
    
    records = []
    for i, chunk in enumerate(chunks):
        records.append({
            "book_name": book_name,
            "chunk_id": f"{book_name}_{i+1}",
            "content": chunk,
            "metadata": {
                "source": source,
                "part": i + 1
            }
        })
        
    return records

def ingest_file(input_path: str, book_name: str) -> List[Dict]:
    """
    Read the file, parse it into chunks, and return a list of structured records.
    """
    if not os.path.exists(input_path):
        logger.error(f"Input file not found: {input_path}")
        return []

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        return []

    return ingest_content(content, book_name, source=input_path)

def save_records(records: List[Dict], output_path: str = "medical_knowledge_db.json"):
    """
    Append records to the JSON DB.
    """
    existing_records = []
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_records = json.load(f)
                if not isinstance(existing_records, list):
                    existing_records = []
        except json.JSONDecodeError:
            pass
            
    all_records = existing_records + records
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    return len(all_records)

def main():
    parser = argparse.ArgumentParser(description="Ingest classical Chinese medical texts for local RAG.")
    parser.add_argument("--input", type=str, required=True, help="Path to the input text file (.txt)")
    parser.add_argument("--output", type=str, default="medical_knowledge_db.json", help="Path to save the JSON database")
    parser.add_argument("--book_name", type=str, required=True, help="Title of the book (e.g. '本經疏證')")
    
    args = parser.parse_args()
    
    records = ingest_file(args.input, args.book_name)
    if not records:
        logger.warning("No records were extracted. Exiting.")
        sys.exit(1)
        
    # Append to existing DB if it exists, or create new
    total = save_records(records, args.output)
    
    logger.info(f"Successfully saved {len(records)} new records to {args.output}")
    logger.info(f"Total records in DB: {total}")

if __name__ == "__main__":
    main()
