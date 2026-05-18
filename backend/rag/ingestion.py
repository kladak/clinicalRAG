import hashlib
import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.retriever import get_encoder, get_or_create_collection

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=64,
    length_function=len,
)


def ingest_document(
    title: str,
    content: str,
    document_type: str,
    source_url: str,
    collection_name: str,
) -> dict:
    document_id = str(uuid.uuid4())
    chunks = splitter.split_text(content)
    collection = get_or_create_collection(collection_name)
    encoder = get_encoder()

    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        chunk_hash = hashlib.sha256(chunk.encode()).hexdigest()
        chunk_id = f"{document_id}_chunk_{i}"

        existing = collection.get(where={"content_hash": chunk_hash})
        if existing and existing["ids"]:
            continue

        ids.append(chunk_id)
        embeddings.append(encoder.encode([chunk])[0].tolist())
        documents.append(chunk)
        metadatas.append(
            {
                "document_id": document_id,
                "title": title,
                "document_type": document_type,
                "source_url": source_url or "",
                "chunk_index": i,
                "total_chunks": len(chunks),
                "content_hash": chunk_hash,
            }
        )

    if ids:
        collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    return {"document_id": document_id, "chunks_created": len(ids)}
