import React, { useState, useEffect } from 'react';
import { Download, Clock, CheckCircle, XCircle, Loader, FileVideo, PlayCircle, Play, Share2, GripVertical, Users, Trash2 } from 'lucide-react';
import axios from 'axios';
import PlayerInfoModal from './PlayerInfoModal';

const StatusBadge = ({ status }) => {
    const styles = {
        completed: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
        processing: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
        failed: 'bg-red-500/10 text-red-400 border-red-500/20',
        queued: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
    };

    const icons = {
        completed: <CheckCircle size={14} />,
        processing: <Loader size={14} className="animate-spin" />,
        failed: <XCircle size={14} />,
        queued: <Clock size={14} />,
    };

    return (
        <span className={`
      inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border
      ${styles[status] || styles.queued}
    `}>
            {icons[status] || icons.queued}
            <span className="capitalize">{status}</span>
        </span>
    );
};

const JobList = ({ jobs, onPlay, onJobDeleted }) => {
    const [showPlayerInfo, setShowPlayerInfo] = useState(false);
    const [playerInfo, setPlayerInfo] = useState(null);
    const [loadingInfoId, setLoadingInfoId] = useState(null);
    const [cleanupHours, setCleanupHours] = useState(24);
    const [deletingJobId, setDeletingJobId] = useState(null);

    useEffect(() => {
        axios.get('/api/config/cleanup')
            .then(res => setCleanupHours(res.data.hours))
            .catch(err => console.error("Failed to fetch cleanup config", err));
    }, []);

    const handleShowPlayerInfo = async (job) => {
        setLoadingInfoId(job.id);
        try {
            const response = await axios.get(`/api/jobs/${job.id}/info`);
            setPlayerInfo(response.data);
            setShowPlayerInfo(true);
        } catch (error) {
            console.error("Failed to fetch player info", error);
            alert("Failed to load player info. It might not be available for this render.");
        } finally {
            setLoadingInfoId(null);
        }
    };

    const handleDelete = async (job) => {
        if (!confirm(`Are you sure you want to delete the job for "${job.filename}"? This cannot be undone.`)) {
            return;
        }
        setDeletingJobId(job.id);
        try {
            await axios.delete(`/api/jobs/${job.id}`);
            if (onJobDeleted) {
                onJobDeleted(job.id);
            }
        } catch (error) {
            console.error("Failed to delete job", error);
            alert("Failed to delete job.");
        } finally {
            setDeletingJobId(null);
        }
    };

    const handleShare = async (job) => {
        try {
            // Show loading state or toast here if possible, but for now just proceed
            const response = await fetch(`/api/download/${job.id}`);
            const blob = await response.blob();
            // job.filename is the .wowsreplay file, we want .mp4
            const filename = job.filename.replace(/\.wowsreplay$/i, '') + '.mp4';
            const file = new File([blob], filename, { type: 'video/mp4' });

            if (navigator.canShare && navigator.canShare({ files: [file] })) {
                await navigator.share({
                    files: [file],
                    title: 'Minimap Render',
                    text: `Check out this render of ${job.filename}`,
                });
            } else {
                // Fallback: Copy link to clipboard
                const url = window.location.origin + `/api/download/${job.id}`;
                await navigator.clipboard.writeText(url);
                alert('Web Share API not supported or file too large. Link copied to clipboard (Note: Link only works on local network).');
            }
        } catch (error) {
            console.error('Error sharing:', error);
            alert('Failed to share video. The file might be too large for the Web Share API.');
        }
    };

    const handleDragStart = (e, job) => {
        const filename = job.filename.replace(/\.wowsreplay$/i, '') + '.mp4';
        const url = new URL(`/api/download/${job.id}`, window.location.origin).href;

        // This format (MIME:filename:url) allows dragging to desktop/apps in Chromium browsers
        e.dataTransfer.setData('DownloadURL', `video/mp4:${filename}:${url}`);
        e.dataTransfer.effectAllowed = 'copy';
    };

    const getExpirationTime = (completedAt) => {
        if (!completedAt) return null;
        // completedAt is likely a string from DB, need to parse
        // Assuming ISO format or similar that Date.parse accepts
        const completedDate = new Date(completedAt);
        const expirationDate = new Date(completedDate.getTime() + cleanupHours * 60 * 60 * 1000);
        const now = new Date();
        const diffMs = expirationDate - now;

        if (diffMs <= 0) return "Expired";

        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

        if (diffHours > 0) {
            return `Expires in ${diffHours}h ${diffMinutes}m`;
        } else {
            return `Expires in ${diffMinutes}m`;
        }
    };

    if (jobs.length === 0) {
        return (
            <div className="text-center py-24 rounded-3xl border border-white/5 bg-slate-900/20 backdrop-blur-sm">
                <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-slate-800/50 flex items-center justify-center">
                    <FileVideo size={32} className="text-slate-600" />
                </div>
                <h3 className="text-lg font-medium text-slate-300 mb-1">No renders yet</h3>
                <p className="text-slate-500 text-sm">Upload a replay to start rendering</p>
            </div>
        );
    }

    return (
        <div className="w-full">
            {/* Mobile Card View (visible below 1400px) */}
            <div className="min-[1400px]:hidden space-y-4">
                {jobs.map((job) => (
                    <div key={job.id} className="p-4 rounded-2xl border border-white/10 bg-slate-900/40 backdrop-blur-xl shadow-lg">
                        <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center gap-3 overflow-hidden">
                                <div className="p-2 rounded-lg bg-slate-800/50 text-slate-400">
                                    <PlayCircle size={20} />
                                </div>
                                <div className="min-w-0">
                                    <h4 className="font-medium text-slate-200 break-all text-sm">{job.filename}</h4>
                                    <div className="mt-1 flex items-center gap-2 flex-wrap">
                                        <StatusBadge status={job.status} />
                                        {job.status === 'completed' && (
                                            <span className="text-[10px] text-slate-500">
                                                {getExpirationTime(job.completed_at)}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                            <button
                                onClick={() => handleDelete(job)}
                                disabled={deletingJobId === job.id}
                                className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                            >
                                {deletingJobId === job.id ? <Loader size={16} className="animate-spin" /> : <Trash2 size={16} />}
                            </button>
                        </div>

                        {job.message && (
                            <p className="text-xs text-slate-400 mb-4 bg-white/5 p-2 rounded-lg break-words">
                                {job.message}
                            </p>
                        )}

                        <div className="flex gap-2 mt-2 flex-wrap">
                            {job.status === 'completed' && (
                                <>
                                    <button
                                        onClick={() => onPlay(job)}
                                        className="flex-1 inline-flex justify-center items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-semibold transition-colors"
                                    >
                                        <Play size={14} />
                                        Watch
                                    </button>
                                    <button
                                        onClick={() => handleShowPlayerInfo(job)}
                                        disabled={loadingInfoId === job.id}
                                        className="inline-flex justify-center items-center gap-2 px-4 py-2 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 rounded-xl text-xs font-semibold transition-colors border border-blue-500/20 disabled:opacity-50"
                                        title="Player Info"
                                    >
                                        {loadingInfoId === job.id ? <Loader size={14} className="animate-spin" /> : <Users size={14} />}
                                    </button>
                                    <button
                                        onClick={() => handleShare(job)}
                                        className="inline-flex justify-center items-center gap-2 px-4 py-2 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 rounded-xl text-xs font-semibold transition-colors border border-indigo-500/20"
                                        title="Share to Discord/Socials"
                                    >
                                        <Share2 size={14} />
                                    </button>
                                    <a
                                        href={`/api/download/${job.id}`}
                                        className="flex-1 inline-flex justify-center items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold transition-colors cursor-grab active:cursor-grabbing"
                                        download
                                        draggable="true"
                                        onDragStart={(e) => handleDragStart(e, job)}
                                        title="Drag to Desktop or Discord"
                                    >
                                        <GripVertical size={14} className="mr-1 opacity-50" />
                                        <Download size={14} />
                                        Download
                                    </a>
                                </>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {/* Desktop Table View (visible at 1400px and above) */}
            <div className="hidden min-[1400px]:block rounded-3xl border border-white/10 bg-slate-900/40 backdrop-blur-xl overflow-hidden shadow-xl">
                <div className="w-full">
                    <table className="w-full text-left text-sm table-fixed">
                        <thead className="bg-white/5 text-slate-400 uppercase text-xs font-medium tracking-wider">
                            <tr>
                                <th className="px-6 py-4 w-48">Status</th>
                                <th className="px-6 py-4">Replay File</th>
                                <th className="px-6 py-4 w-64">Details</th>
                                <th className="px-6 py-4 text-right w-[400px]">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {jobs.map((job) => (
                                <tr key={job.id} className="group hover:bg-white/[0.02] transition-colors duration-200">
                                    <td className="px-6 py-4 whitespace-nowrap align-top">
                                        <div className="flex flex-col gap-1">
                                            <StatusBadge status={job.status} />
                                            {job.status === 'completed' && (
                                                <span className="text-[10px] text-slate-500 ml-1">
                                                    {getExpirationTime(job.completed_at)}
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 align-top">
                                        <div className="flex items-start gap-3">
                                            <div className="p-2 rounded-lg bg-slate-800/50 text-slate-400 group-hover:text-blue-400 transition-colors shrink-0 mt-0.5">
                                                <PlayCircle size={18} />
                                            </div>
                                            <span className="font-medium text-slate-200 break-all" title={job.filename}>
                                                {job.filename}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-slate-400 align-top">
                                        <div className="break-words">
                                            {job.message || <span className="text-slate-600 italic">No details</span>}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-right whitespace-nowrap align-top">
                                        <div className="flex items-center justify-end gap-2">
                                            {job.status === 'completed' && (
                                                <>
                                                    <button
                                                        onClick={() => onPlay(job)}
                                                        className="
                                inline-flex items-center gap-2 px-3 py-2 
                                bg-white/5 hover:bg-white/10 
                                text-slate-200 rounded-xl text-xs font-semibold 
                                transition-all duration-200
                              "
                                                    >
                                                        <Play size={14} />
                                                        Watch
                                                    </button>
                                                    <button
                                                        onClick={() => handleShowPlayerInfo(job)}
                                                        disabled={loadingInfoId === job.id}
                                                        className="
                                inline-flex items-center gap-2 px-3 py-2 
                                bg-blue-500/10 hover:bg-blue-500/20 
                                text-blue-400 rounded-xl text-xs font-semibold 
                                transition-all duration-200 border border-blue-500/20 disabled:opacity-50
                              "
                                                        title="Player Info"
                                                    >
                                                        {loadingInfoId === job.id ? <Loader size={14} className="animate-spin" /> : <Users size={14} />}
                                                    </button>
                                                    <button
                                                        onClick={() => handleShare(job)}
                                                        className="
                                inline-flex items-center gap-2 px-3 py-2 
                                bg-indigo-500/10 hover:bg-indigo-500/20 
                                text-indigo-400 rounded-xl text-xs font-semibold 
                                transition-all duration-200 border border-indigo-500/20
                              "
                                                        title="Share"
                                                    >
                                                        <Share2 size={14} />
                                                    </button>
                                                    <a
                                                        href={`/api/download/${job.id}`}
                                                        className="
                                inline-flex items-center gap-2 px-4 py-2 
                                bg-blue-600 hover:bg-blue-500 active:bg-blue-700
                                text-white rounded-xl text-xs font-semibold 
                                transition-all duration-200 shadow-lg shadow-blue-500/20 hover:shadow-blue-500/40 hover:-translate-y-0.5
                                cursor-grab active:cursor-grabbing
                              "
                                                        download
                                                        draggable="true"
                                                        onDragStart={(e) => handleDragStart(e, job)}
                                                        title="Drag to Desktop or Discord"
                                                    >
                                                        <GripVertical size={14} className="mr-1 opacity-50" />
                                                        <Download size={14} />
                                                        Download
                                                    </a>
                                                </>
                                            )}
                                            <button
                                                onClick={() => handleDelete(job)}
                                                disabled={deletingJobId === job.id}
                                                className="
                            inline-flex items-center gap-2 px-3 py-2 
                            bg-red-500/10 hover:bg-red-500/20 
                            text-red-400 rounded-xl text-xs font-semibold 
                            transition-all duration-200 border border-red-500/20
                          "
                                                title="Delete Job"
                                            >
                                                {deletingJobId === job.id ? <Loader size={14} className="animate-spin" /> : <Trash2 size={14} />}
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {showPlayerInfo && (
                <PlayerInfoModal
                    players={playerInfo}
                    onClose={() => setShowPlayerInfo(false)}
                />
            )}
        </div>
    );
};

export default JobList;
