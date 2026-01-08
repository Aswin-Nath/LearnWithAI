import re  
import pymupdf4llm
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from pathlib import Path
from langchain_core.documents import Document

PERSIST_DIR = str(Path(__file__).parent.parent / "ai/chroma_db")
embeddings = HuggingFaceEmbeddings(model_name="all-mpnet-base-v2")

def ingest_pdf_from_file(file_path: str, problem_id: int) -> dict:
    """
    Ingest a PDF file into Chroma vector DB for a specific problem.
    
    Args:
        file_path: Path to the PDF file
        problem_id: Problem ID to associate with the ingested content
    
    Returns:
        dict with success status and message
    """
    path = Path(file_path)
    if not path.exists():
        return {
            "success": False,
            "message": f"File not found: {file_path}",
            "chunks_uploaded": 0
        }

    try:
        md_text = pymupdf4llm.to_markdown(str(path))
        md_text = re.sub(r'^\*\*(.*?)\*\*$', r'## \1', md_text, flags=re.MULTILINE)
        md_text = re.sub(r'^## (Approach \d+.*)$', r'### \1', md_text, flags=re.MULTILINE)
        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Title"),
                ("##", "Section"),
                ("###", "Subsection"),
            ]
        )
        chunks = splitter.split_text(md_text)
        documents = []
        for chunk in chunks:
            section_path = " > ".join(chunk.metadata.values())
            if not section_path:
                section_path = "General"
            doc = Document(
                page_content=chunk.page_content.strip(),
                metadata={
                    "problem_id": problem_id,
                    "section": section_path,
                    "source": path.name
                }
            )
            documents.append(doc)
        collection_name = f"problem_{problem_id}"
        Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=PERSIST_DIR,
            collection_name=collection_name
        )
        return {
            "success": True,
            "message": f"Successfully ingested PDF into knowledge base",
            "chunks_uploaded": len(documents)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to process PDF: {str(e)}",
            "chunks_uploaded": 0
        }