from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from pathlib import Path
from langchain_core.documents import Document

PROBLEM_ID = 3
FILE_NAME="editorial/three_sum.md"
MD_FILE = Path(__file__).parent.parent / FILE_NAME
PERSIST_DIR = str(Path(__file__).parent.parent / "chroma_db")
COLLECTION_NAME = f"problem_{PROBLEM_ID}"

embeddings = HuggingFaceEmbeddings(model_name="all-mpnet-base-v2")

def ingest_markdown(md_path: str):
    text = Path(md_path).read_text(encoding="utf-8")

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "Title"),
            ("##", "Section"),
            ("###", "Subsection"),
            ("####", "Detail"),
        ]
    )

    chunks = splitter.split_text(text)
    
    # Convert chunks to LangChain Document format
    documents = []
    for chunk in chunks:
        section_path = " > ".join(chunk.metadata.values())
        doc = Document(
            page_content=chunk.page_content.strip(),
            metadata={
                "problem_id": PROBLEM_ID,
                "section": section_path
            }
        )
        documents.append(doc)
    vectordb = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
        collection_name=COLLECTION_NAME,
        collection_metadata={"hnsw:space": "cosine"}
    )
    return vectordb

if __name__ == "__main__":
    print(f"📁 MD_FILE: {MD_FILE}")
    print(f"📁 PERSIST_DIR: {PERSIST_DIR}")
    print(f"📋 COLLECTION_NAME: {COLLECTION_NAME}")
    print()
    
    if not MD_FILE.exists():
        print(f"❌ ERROR: Markdown file not found at {MD_FILE}")
        exit(1)
    
    print("🚀 Starting ingestion...")
    vectordb = ingest_markdown(str(MD_FILE))
    print(f"✅ Ingestion complete! Documents stored in {PERSIST_DIR}")
    print(f"✅ Collection: {COLLECTION_NAME}")
    

