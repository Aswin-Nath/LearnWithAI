"""
Markdown Editorial Upload Utility
Handles uploading and ingesting markdown files into Chroma vector store
"""

from pathlib import Path
from typing import Optional, List, Dict

from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document


class MarkdownEditoralUploader:
    """Upload and ingest markdown files into Chroma vector store."""
    
    def __init__(self):
        """Initialize uploader with Chroma connection and embeddings."""
        # Get app directory using pathlib
        current_file = Path(__file__)
        # Navigate: md_upload_util.py -> utils -> app
        self.app_dir = current_file.parent.parent
        self.persist_dir = str(self.app_dir / "chroma_db")
        
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(model_name="all-mpnet-base-v2")
        
        print(f"📁 Using Chroma DB at: {self.persist_dir}")
    
    def _read_markdown_file(self, file_path: str) -> str:
        """Read markdown file and return content."""
        return Path(file_path).read_text(encoding="utf-8")
    
    def _split_markdown(self, content: str) -> List[Document]:
        """
        Split markdown by headers using MarkdownHeaderTextSplitter.
        
        This preserves the hierarchical structure of the markdown.
        """
        # Define headers to split on
        headers_to_split_on = [
            ("#", "Title"),
            ("##", "Section"),
            ("###", "Subsection"),
            ("####", "Detail"),
        ]
        
        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on
        )
        
        # Split the markdown
        chunks = splitter.split_text(content)
        
        print(f"✂️  Split into {len(chunks)} sections")
        return chunks
    
    def upload_markdown(
        self,
        file_path: str,
        problem_id: int,
        clear_existing: bool = False
    ) -> Dict[str, any]:
        """
        Upload a markdown file to Chroma.
        
        Args:
            file_path: Path to the markdown file
            problem_id: Problem ID this editorial is for
            clear_existing: Whether to clear existing documents before adding
            
        Returns:
            Dict with upload status and details
        """
        try:
            # Validate file exists
            md_path = Path(file_path)
            if not md_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "problem_id": problem_id
                }
            
            # Check it's a markdown file
            if not str(file_path).lower().endswith('.md'):
                return {
                    "success": False,
                    "error": "File must be a markdown (.md) file",
                    "problem_id": problem_id
                }
            
            print(f"📖 Uploading markdown for problem {problem_id}: {md_path.name}")
            
            # Read the markdown file
            content = self._read_markdown_file(str(md_path))
            print(f"📄 File size: {len(content)} characters")
            
            # Split by headers
            chunks = self._split_markdown(content)
            
            # Convert chunks to Document format with metadata
            documents = []
            for chunk in chunks:
                # Build section path from metadata
                section_path = " > ".join(str(v) for v in chunk.metadata.values() if v)
                
                doc = Document(
                    page_content=chunk.page_content.strip(),
                    metadata={
                        "problem_id": problem_id,
                        "section": section_path
                    }
                )
                documents.append(doc)
            
            print(f"📝 Prepared {len(documents)} documents with metadata")
            
            # Get collection name
            collection_name = f"problem_{problem_id}"
            
            # Clear existing if requested
            if clear_existing:
                try:
                    # Delete the collection by creating a new one
                    vectordb = Chroma(
                        collection_name=collection_name,
                        embedding_function=self.embeddings,
                        persist_directory=self.persist_dir
                    )
                    vectordb.delete_collection()
                    print("🗑️  Cleared existing documents")
                except Exception as e:
                    print(f"⚠️  Could not clear existing: {e}")
            
            # Ingest using Chroma.from_documents
            vectordb = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=self.persist_dir,
                collection_name=collection_name,
                collection_metadata={"hnsw:space": "cosine"}
            )
            
            print(f"✅ Successfully uploaded {len(documents)} chunks to Chroma")
            
            return {
                "success": True,
                "problem_id": problem_id,
                "chunks_uploaded": len(documents),
                "file_path": str(file_path),
                "collection_name": collection_name,
                "message": f"Successfully uploaded {len(documents)} chunks"
            }
            
        except Exception as e:
            print(f"❌ Error uploading markdown: {e}")
            return {
                "success": False,
                "error": str(e),
                "problem_id": problem_id
            }
    
    def upload_directory(
        self,
        directory_path: str,
        problem_id: int,
        pattern: str = "*.md"
    ) -> Dict[str, any]:
        """
        Upload all markdown files from a directory.
        
        Args:
            directory_path: Path to directory containing markdown files
            problem_id: Problem ID
            pattern: File pattern to match (default: *.md)
            
        Returns:
            Dict with upload results
        """
        dir_path = Path(directory_path)
        if not dir_path.is_dir():
            return {
                "success": False,
                "error": f"Directory not found: {directory_path}"
            }
        
        # Find all markdown files
        md_files = list(dir_path.glob(pattern))
        
        if not md_files:
            return {
                "success": False,
                "error": f"No markdown files found in {directory_path}"
            }
        
        results = []
        for md_file in md_files:
            print(f"\n📂 Processing: {md_file.name}")
            result = self.upload_markdown(str(md_file), problem_id)
            results.append(result)
        
        # Summary
        successful = sum(1 for r in results if r.get("success"))
        print(f"\n📊 Upload summary: {successful}/{len(results)} files uploaded successfully")
        
        return {
            "success": successful == len(results),
            "total_files": len(md_files),
            "successful": successful,
            "details": results
        }


# Convenience function for quick uploads
uploader = MarkdownEditoralUploader()

def upload_markdown_editorial(
    file_path: str,
    problem_id: int,
    clear_existing: bool = False
) -> Dict[str, any]:
    """
    Quick function to upload a markdown file.
    
    Usage:
        result = upload_markdown_editorial("path/to/file.md", problem_id=1)
    """
    return uploader.upload_markdown(file_path, problem_id, clear_existing)
