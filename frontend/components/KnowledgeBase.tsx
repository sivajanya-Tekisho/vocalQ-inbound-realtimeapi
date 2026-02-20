
import React, { useState } from 'react';
import { COLORS } from '../constants';

const MAX_FILE_SIZE = 15 * 1024 * 1024; // 15 MB in bytes

interface KBDocument {
    id: string;
    filename: string;
    upload_date: string;
    chunk_count: number;
    file_size: number;
}

const KnowledgeBase: React.FC = () => {
    const [documents, setDocuments] = useState<KBDocument[]>([]);
    const [uploading, setUploading] = useState(false);
    const [dragOver, setDragOver] = useState(false);

    const fetchDocuments = async () => {
        try {
            const res = await fetch('http://localhost:8000/api/v1/knowledge-base/list');
            if (!res.ok) throw new Error('Failed to fetch documents');
            const data = await res.json();
            setDocuments(data.documents || []);
        } catch (e) {
            console.error('Error fetching documents:', e);
            setDocuments([]);
        }
    };

    React.useEffect(() => { fetchDocuments(); }, []);

    const handleUpload = async (file: File) => {
        // Check file size (15 MB limit)
        if (file.size > MAX_FILE_SIZE) {
            alert(`File size exceeds the limit. Maximum accepted file size is 15 MB.\n\nFile: ${file.name}\nSize: ${(file.size / (1024 * 1024)).toFixed(2)} MB`);
            return;
        }

        setUploading(true);
        try {
            const formData = new FormData();
            formData.append('file', file);
            const res = await fetch('http://localhost:8000/api/v1/knowledge-base/upload', {
                method: 'POST',
                body: formData
            });
            if (!res.ok) {
                const error = await res.json();
                throw new Error(error.detail || 'Upload failed');
            }
            await fetchDocuments();
        } catch (e: any) {
            console.error('Error uploading document:', e);
            alert(e.message || 'Failed to upload document. Please try again.');
        } finally {
            setUploading(false);
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm('Are you sure you want to delete this document?')) return;
        try {
            const res = await fetch(`http://localhost:8000/api/v1/knowledge-base/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Failed to delete document');
            await fetchDocuments();
        } catch (e) {
            console.error('Error deleting document:', e);
            alert('Failed to delete document. Please try again.');
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault(); setDragOver(false);
        const file = e.dataTransfer.files[0];
        if (file) handleUpload(file);
    };

    const formatSize = (bytes: number) => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    };

    return (
        <div style={{ paddingTop: '24px' }}>
            <div style={{ marginBottom: '32px' }}>
                <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#0F172A', marginBottom: '4px', fontFamily: 'Inter, system-ui, sans-serif' }}>
                    Knowledge Base
                </h2>
                <p style={{ fontSize: '14px', color: '#94A3B8' }}>
                    Upload documents for the AI assistant's RAG pipeline
                </p>
            </div>

            {/* Upload Area */}
            <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                style={{
                    backgroundColor: dragOver ? '#FFF7ED' : '#FFFFFF',
                    border: `2px dashed ${dragOver ? COLORS.primary : '#E2E8F0'}`,
                    borderRadius: '16px', padding: '48px', textAlign: 'center',
                    marginBottom: '32px', transition: 'all 0.2s', cursor: 'pointer',
                }}
                onClick={() => {
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.accept = '.pdf,.txt,.docx';
                    input.onchange = (e: any) => {
                        const file = e.target.files?.[0];
                        if (file) handleUpload(file);
                    };
                    input.click();
                }}
            >
                <div style={{
                    width: '56px', height: '56px', borderRadius: '14px',
                    backgroundColor: '#FFF7ED', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    margin: '0 auto 16px',
                }}>
                    <svg width="28" height="28" fill="none" stroke={COLORS.primary} viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                </div>
                <h3 style={{ fontSize: '16px', fontWeight: '600', color: '#0F172A', marginBottom: '4px' }}>
                    {uploading ? 'Uploading...' : 'Drop files here or click to upload'}
                </h3>
                <p style={{ fontSize: '13px', color: '#94A3B8' }}>
                    Supports PDF, TXT, DOCX
                </p>
            </div>

            {/* Documents List */}
            <div style={{
                backgroundColor: '#FFFFFF', borderRadius: '16px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.06)', overflow: 'hidden',
            }}>
                <div style={{ padding: '20px 24px', borderBottom: '1px solid #E2E8F0' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: '600', color: '#0F172A' }}>
                        Uploaded Documents ({documents.length})
                    </h3>
                </div>

                {documents.length === 0 ? (
                    <div style={{ padding: '48px', textAlign: 'center' }}>
                        <p style={{ fontSize: '14px', color: '#94A3B8' }}>No documents uploaded yet.</p>
                    </div>
                ) : (
                    <div>
                        {documents.map((doc, idx) => (
                            <div key={doc.id} style={{
                                padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                borderBottom: idx < documents.length - 1 ? '1px solid #F1F5F9' : 'none',
                                transition: 'background-color 0.2s',
                            }}
                                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#FAFAFA'}
                                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                                    <div style={{
                                        width: '40px', height: '40px', borderRadius: '10px', backgroundColor: '#F1F5F9',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    }}>
                                        <svg width="20" height="20" fill="none" stroke="#64748B" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                        </svg>
                                    </div>
                                    <div>
                                        <p style={{ fontSize: '14px', fontWeight: '600', color: '#0F172A' }}>{doc.filename}</p>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
                                            <span style={{ fontSize: '12px', color: '#94A3B8' }}>{formatSize(doc.file_size)}</span>
                                            <span style={{ width: '3px', height: '3px', borderRadius: '50%', backgroundColor: '#CBD5E1', display: 'inline-block' }} />
                                            <span style={{ fontSize: '12px', color: '#94A3B8' }}>{doc.chunk_count} chunks</span>
                                            <span style={{ width: '3px', height: '3px', borderRadius: '50%', backgroundColor: '#CBD5E1', display: 'inline-block' }} />
                                            <span style={{ fontSize: '12px', color: '#94A3B8' }}>{new Date(doc.upload_date).toLocaleDateString()}</span>
                                        </div>
                                    </div>
                                </div>
                                <button
                                    onClick={() => handleDelete(doc.id)}
                                    style={{
                                        padding: '8px 16px', backgroundColor: '#FEF2F2', border: '1px solid #FECACA',
                                        borderRadius: '8px', color: '#EF4444', fontWeight: '600', fontSize: '12px',
                                        cursor: 'pointer', transition: 'all 0.2s',
                                    }}
                                    onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#FEE2E2'; }}
                                    onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#FEF2F2'; }}
                                >
                                    Delete
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default KnowledgeBase;
