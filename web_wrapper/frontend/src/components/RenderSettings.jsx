import React from 'react';
import { Settings, UserX, MessageSquareOff, FileText, Users, Gauge, MonitorPlay } from 'lucide-react';

const RenderSettings = ({ settings, setSettings }) => {
  const handleChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="bg-slate-900/50 rounded-2xl p-6 border border-white/10 backdrop-blur-sm w-full max-w-3xl mx-auto">
      <div className="flex items-center gap-2 mb-6 text-white/90">
        <Settings size={20} className="text-blue-400" />
        <h3 className="font-semibold text-lg">Render Settings</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Toggles */}
        <div className="space-y-4">
          <Toggle
            label="Anonymize Players"
            icon={UserX}
            checked={settings.anon}
            onChange={(v) => handleChange('anon', v)}
            description="Hide player names in the minimap"
          />
          <Toggle
            label="Disable Chat"
            icon={MessageSquareOff}
            checked={settings.no_chat}
            onChange={(v) => handleChange('no_chat', v)}
            description="Hide in-game chat messages"
          />
          <Toggle
            label="Disable Logs"
            icon={FileText}
            checked={settings.no_logs}
            onChange={(v) => handleChange('no_logs', v)}
            description="Hide damage logs and ribbons"
          />
          <Toggle
            label="Team Tracers"
            icon={Users}
            checked={settings.team_tracers}
            onChange={(v) => handleChange('team_tracers', v)}
            description="Show tracers for all teammates"
          />
        </div>

        {/* Sliders */}
        <div className="space-y-6">
          <RangeInput
            label="Frame Rate (FPS)"
            icon={Gauge}
            value={settings.fps}
            min={10}
            max={60}
            step={5}
            onChange={(v) => handleChange('fps', v)}
            suffix=" FPS"
          />
          <RangeInput
            label="Video Quality"
            icon={MonitorPlay}
            value={settings.quality}
            min={1}
            max={10}
            step={1}
            onChange={(v) => handleChange('quality', v)}
            description="Higher is better but larger file size"
          />
        </div>
      </div>
    </div>
  );
};

const Toggle = ({ label, icon: Icon, checked, onChange, description }) => (
  <div className="flex items-start gap-3 group cursor-pointer select-none" onClick={() => onChange(!checked)}>
    <div className={`mt-1 w-5 h-5 rounded border flex items-center justify-center transition-colors ${checked ? 'bg-blue-500 border-blue-500' : 'border-slate-500 bg-transparent group-hover:border-blue-400'}`}>
      {checked && <div className="w-2.5 h-2.5 bg-white rounded-sm" />}
    </div>
    <div className="flex-1">
      <div className="flex items-center gap-2 text-white font-medium text-sm">
        <Icon size={16} className="text-slate-400" />
        {label}
      </div>
      {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
    </div>
  </div>
);

const RangeInput = ({ label, icon: Icon, value, min, max, step, onChange, suffix = '', description }) => (
  <div>
    <div className="flex justify-between items-center mb-2">
      <div className="flex items-center gap-2 text-white font-medium text-sm">
        <Icon size={16} className="text-slate-400" />
        {label}
      </div>
      <span className="text-blue-400 font-mono text-sm">{value}{suffix}</span>
    </div>
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500 hover:accent-blue-400"
    />
    {description && <p className="text-xs text-slate-500 mt-1.5">{description}</p>}
  </div>
);

export default RenderSettings;
