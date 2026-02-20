"""
Knowledge Base Management Endpoints
Handles document upload, deletion, and listing.
"""

import logging
import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Optional

from app.services.document_ingestion_service import DocumentIngestionService
from app.core.supabase_client import supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])

# Initialize service
doc_ingestion = DocumentIngestionService()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """
    Upload a document to the knowledge base.
    Also tracks the upload in the knowledge_base_documents Supabase table.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate file type
    allowed_extensions = {".pdf", ".txt", ".docx"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported: {', '.join(allowed_extensions)}"
        )
    
    temp_path = None
    # Save uploaded file to temp location
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await file.read()
            
            # Check file size (15 MB limit)
            file_size = len(content)
            file_size_mb = file_size / (1024 * 1024)
            if file_size_mb > 15:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds the limit. Maximum accepted file size is 15 MB. Your file: {file_size_mb:.2f} MB"
                )
            
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Prepare metadata
        metadata = {}
        if category:
            metadata["category"] = category
        if description:
            metadata["description"] = description
        
        # Ingest document
        result = await doc_ingestion.ingest_document(
            file_path=temp_path,
            file_name=file.filename,
            metadata=metadata
        )
        
        # Track upload in Supabase knowledge_base_documents table
        if result.get("success"):
            try:
                doc_id = result.get("doc_id", "")
                supabase.table("knowledge_base_documents").insert({
                    "doc_id": doc_id,
                    "filename": file.filename,
                    "file_size": file_size,
                    "file_type": file_ext.lstrip("."),
                    "uploaded_by": "system",  # Will be updated when auth is implemented
                    "chunk_count": result.get("chunks", 0),
                    "status": "ready",
                    "metadata": metadata
                }).execute()
                logger.info(f"Tracked upload in Supabase: {file.filename} ({doc_id})")
            except Exception as db_err:
                logger.warning(f"Failed to track upload in Supabase: {db_err}")
        
        return JSONResponse(content=result, status_code=200 if result["success"] else 400)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")
    
    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

@router.get("/list")
async def list_documents():
    """
    List all ingested documents in the knowledge base.
    
    Returns:
        List of documents with their metadata
    """
    try:
        raw_documents = doc_ingestion.list_documents()
        
        # Transform to frontend-expected format
        documents = []
        for doc in raw_documents:
            doc_id = doc.get("doc_id", "unknown")
            doc_dir = doc_ingestion.knowledge_base_dir / doc_id
            
            # Get file info
            files = doc.get("files", [])
            filename = files[0] if files else "Unknown Document"
            
            # Get file size
            file_size = 0
            upload_date = None
            if doc_dir.exists():
                for file_path in doc_dir.glob("*"):
                    if file_path.is_file():
                        import os
                        from datetime import datetime
                        file_size = file_path.stat().st_size
                        upload_date = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                        break
            
            documents.append({
                "id": doc_id,
                "filename": filename,
                "upload_date": upload_date or "Unknown",
                "chunk_count": doc.get("file_count", 0),
                "file_size": file_size
            })
        
        return JSONResponse(
            content={
                "success": True,
                "count": len(documents),
                "documents": documents
            }
        )
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        # Return empty list instead of error to prevent UI breaking
        return JSONResponse(
            content={
                "success": True,
                "count": 0,
                "documents": [],
                "warning": str(e)
            }
        )

@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """
    Delete a document and all its chunks from the knowledge base.
    Also removes the record from the knowledge_base_documents table.
    """
    try:
        result = await doc_ingestion.delete_document(doc_id)
        
        # Also remove from Supabase tracking table
        if result.get("success"):
            try:
                supabase.table("knowledge_base_documents").delete().eq("doc_id", doc_id).execute()
                logger.info(f"Removed {doc_id} from knowledge_base_documents table")
            except Exception as db_err:
                logger.warning(f"Failed to remove from Supabase: {db_err}")
        
        status_code = 200 if result["success"] else 400
        return JSONResponse(content=result, status_code=status_code)
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

@router.get("/info")
async def knowledge_base_info():
    """
    Get information about the knowledge base.
    
    Returns:
        Knowledge base statistics
    """
    try:
        documents = doc_ingestion.list_documents()
        total_files = sum(doc["file_count"] for doc in documents)
        
        return JSONResponse(
            content={
                "status": "operational",
                "total_documents": len(documents),
                "total_files": total_files,
                "supported_formats": ["pdf", "txt", "docx"],
                "chunk_size": doc_ingestion.chunk_size,
                "chunk_overlap": doc_ingestion.chunk_overlap,
                "embedding_model": "OpenAI text-embedding-3-small",
                "vector_database": "Qdrant"
            }
        )
    except Exception as e:
        logger.error(f"Error getting KB info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting KB info: {str(e)}")
