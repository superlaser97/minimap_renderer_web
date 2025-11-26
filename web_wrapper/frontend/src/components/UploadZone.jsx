import React, { useCallback, useState } from 'react';
import { Upload, File, X, AlertCircle, Film } from 'lucide-react';
import axios from 'axios';

const UploadZone = ({ onUploadComplete }) => {
    const [isDragging, setIsDragging] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState(null);

    const handleDrag = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setIsDragging(true);
        } else if (e.type === 'dragleave') {
            setIsDragging(false);
        }
    }, []);

    const handleDrop = useCallback(async (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
        setError(null);

        const files = [...e.dataTransfer.files];
        if (files.length === 0) return;

        await uploadFiles(files);
    }, []);

    const handleFileInput = async (e) => {
        const files = [...e.target.files];
        if (files.length === 0) return;
        await uploadFiles(files);
    };

    const uploadFiles = async (files) => {
        setUploading(true);
        setError(null);

        const validFiles = files.filter(f => f.name.endsWith('.wowsreplay'));

        if (validFiles.length === 0 && files.length > 0) {
            setError("Please upload .wowsreplay files only.");
            setUploading(false);
            return;
        }

        try {
            const uploads = validFiles.map(file => {
                const formData = new FormData();
                formData.append('file', file);
                return axios.post('/api/upload', formData);
            });

            await Promise.all(uploads);
            onUploadComplete();
        } catch (err) {
            console.error("Upload failed", err);
            setError("Failed to upload one or more files.");
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="w-full max-w-3xl mx-auto">
            <div
                className={`
          relative group cursor-pointer overflow-hidden
          rounded-3xl border-2 transition-all duration-300 ease-out
          ${isDragging
                        ? 'border-blue-500 bg-blue-500/10 scale-[1.02] shadow-2xl shadow-blue-500/20'
                        : 'border-white/10 bg-slate-900/40 hover:border-blue-500/50 hover:bg-slate-900/60'
                    }
          backdrop-blur-xl
        `}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => document.getElementById('file-input').click()}
            >
                <input
                    id="file-input"
                    type="file"
                    multiple
                    accept=".wowsreplay"
                    className="hidden"
                    onChange={handleFileInput}
                />

                <div className="relative py-16 px-8 flex flex-col items-center justify-center text-center z-10">
                    <div className={`
            p-6 rounded-full mb-6 transition-all duration-300
            ${isDragging ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/50' : 'bg-white/5 text-blue-400 group-hover:bg-blue-500/20 group-hover:scale-110'}
          `}>
                        {uploading ? (
                            <div className="animate-spin">
                                <Film size={40} />
                            </div>
                        ) : (
                            <Upload size={40} strokeWidth={1.5} />
                        )}
                    </div>

                    <h3 className="text-2xl font-semibold text-white mb-2">
                        {uploading ? 'Uploading Replays...' : 'Drop Replays Here'}
                    </h3>

                    <p className="text-slate-400 text-sm max-w-sm mx-auto leading-relaxed">
                        {uploading
                            ? 'Please wait while we process your files.'
                            : 'Support for .wowsreplay files. Batch upload supported.'
                        }
                    </p>

                    {!uploading && (
                        <div className="mt-8 px-6 py-2 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-slate-400 group-hover:bg-white/10 transition-colors">
                            Click to browse files
                        </div>
                    )}
                </div>

                {/* Decorative gradient background */}
                <div className={`
          absolute inset-0 bg-gradient-to-tr from-blue-500/5 via-transparent to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none
        `} />
            </div>

            {error && (
                <div className="mt-4 flex items-center justify-center gap-2 text-red-400 bg-red-500/10 border border-red-500/20 p-4 rounded-xl text-sm animate-in fade-in slide-in-from-top-2">
                    <AlertCircle size={16} />
                    {error}
                </div>
            )}
        </div>
    );
};

export default UploadZone;
