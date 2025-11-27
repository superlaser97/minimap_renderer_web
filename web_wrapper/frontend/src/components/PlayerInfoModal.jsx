import React from 'react';
import { X, ExternalLink, Anchor, Users, Shield } from 'lucide-react';

const PlayerInfoModal = ({ players, onClose }) => {
    if (!players) return null;

    // Group players by relation (team)
    const teams = players.reduce((acc, player) => {
        const relation = player.relation;
        if (!acc[relation]) acc[relation] = [];
        acc[relation].push(player);
        return acc;
    }, {});

    // Sort relations to ensure consistent order (e.g., Ally (0), Enemy (1), etc.)
    const sortedRelations = Object.keys(teams).sort((a, b) => a - b);

    const getRelationLabel = (relation) => {
        switch (parseInt(relation)) {
            case 0: return 'Allies';
            case 1: return 'Enemies';
            case 2: return 'Neutral'; // If applicable
            default: return 'Unknown';
        }
    };

    const getRelationColor = (relation) => {
        switch (parseInt(relation)) {
            case 0: return 'text-green-400 bg-green-400/10 border-green-400/20';
            case 1: return 'text-red-400 bg-red-400/10 border-red-400/20';
            default: return 'text-slate-400 bg-slate-400/10 border-slate-400/20';
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="relative w-full max-w-4xl bg-slate-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">

                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-white/10 bg-slate-900/50 backdrop-blur-md sticky top-0 z-10">
                    <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                        <Users className="w-5 h-5 text-blue-400" />
                        Player Information
                    </h3>
                    <button
                        onClick={onClose}
                        className="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="overflow-y-auto p-6 space-y-8">
                    {sortedRelations.map((relation) => (
                        <div key={relation} className="space-y-4">
                            <h4 className={`text-sm font-bold uppercase tracking-wider px-3 py-1 rounded-full w-fit border ${getRelationColor(relation)}`}>
                                {getRelationLabel(relation)}
                            </h4>

                            <div className="overflow-x-auto rounded-xl border border-white/5 bg-white/5">
                                <table className="w-full text-left text-sm">
                                    <thead className="bg-white/5 text-slate-400 uppercase text-xs font-semibold">
                                        <tr>
                                            <th className="px-6 py-4">Player</th>
                                            <th className="px-6 py-4">Clan</th>
                                            <th className="px-6 py-4">Ship</th>
                                            <th className="px-6 py-4 text-right">Build</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {teams[relation].map((player, idx) => (
                                            <tr key={idx} className="hover:bg-white/5 transition-colors">
                                                <td className="px-6 py-4 font-medium text-white">
                                                    {player.name}
                                                </td>
                                                <td className="px-6 py-4 text-slate-300">
                                                    {player.clan ? (
                                                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-white/5 text-slate-300 text-xs font-medium border border-white/5">
                                                            <Shield size={12} />
                                                            [{player.clan}]
                                                        </span>
                                                    ) : (
                                                        <span className="text-slate-600">-</span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4 text-slate-300 flex items-center gap-2">
                                                    <Anchor size={14} className="text-slate-500" />
                                                    {player.ship}
                                                </td>
                                                <td className="px-6 py-4 text-right">
                                                    {player.build_url ? (
                                                        <a
                                                            href={player.build_url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="inline-flex items-center gap-1.5 text-blue-400 hover:text-blue-300 transition-colors text-xs font-medium hover:underline"
                                                        >
                                                            View Build
                                                            <ExternalLink size={12} />
                                                        </a>
                                                    ) : (
                                                        <span className="text-slate-600 text-xs">No Build</span>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default PlayerInfoModal;
