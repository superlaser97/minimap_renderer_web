import React, { useEffect, useState } from 'react';
import axios from 'axios';
import UploadZone from './components/UploadZone';
import JobList from './components/JobList';
import VideoModal from './components/VideoModal';
import { Ship, Download } from 'lucide-react';

function App() {
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);

  const fetchJobs = async () => {
    try {
      const response = await axios.get('/api/jobs');
      setJobs(response.data.reverse());
    } catch (error) {
      console.error("Failed to fetch jobs", error);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-blue-500/20 rounded-full blur-[120px] -z-10 pointer-events-none" />

      <div className="max-w-[95%] mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-16">
        <header className="mb-12 md:mb-16 text-center relative z-10">
          <div className="inline-flex items-center justify-center p-3 mb-6 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-white/10 shadow-2xl shadow-blue-500/10 backdrop-blur-sm">
            <Ship className="w-8 h-8 text-blue-400" />
          </div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 tracking-tight">
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-white via-blue-100 to-blue-200">
              Minimap Renderer
            </span>
          </h1>
          <p className="text-base md:text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed px-4">
            Transform your World of Warships replays into stunning cinematic minimap timelapses.
            Drag, drop, and render.
          </p>
        </header>

        <main className="grid grid-cols-1 min-[1400px]:grid-cols-12 gap-8 relative z-10 items-start">
          <section className="min-[1400px]:col-span-5 min-[1600px]:col-span-4 transform hover:scale-[1.01] transition-transform duration-500">
            <div className="min-[1400px]:sticky min-[1400px]:top-8">
              <UploadZone onUploadComplete={fetchJobs} />
            </div>
          </section>

          <section className="min-[1400px]:col-span-7 min-[1600px]:col-span-8">
            <div className="flex items-center justify-between mb-6 px-2">
              <h2 className="text-xl md:text-2xl font-semibold text-white flex items-center gap-3">
                <span className="w-1 h-8 bg-blue-500 rounded-full block"></span>
                Rendering Queue
              </h2>
              <div className="flex items-center gap-3">
                {jobs.some(j => j.status === 'completed') && (
                  <a
                    href="/api/download-all"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-full text-sm font-medium transition-colors border border-white/10"
                    download
                  >
                    <Download size={16} />
                    Download All
                  </a>
                )}
                <span className="text-sm text-slate-500 font-medium px-3 py-1 rounded-full bg-white/5 border border-white/5">
                  {jobs.length} {jobs.length === 1 ? 'Job' : 'Jobs'}
                </span>
              </div>
            </div>
            <JobList jobs={jobs} onPlay={setSelectedJob} />
          </section>
        </main>

        <footer className="mt-24 text-center text-slate-600 text-sm space-y-2">
          <p>
            Powered by <a href="https://github.com/WoWs-Builder-Team/minimap_renderer" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 transition-colors">Minimap Renderer Engine</a>
          </p>
          <p className="text-slate-700">Made by Ducky &lt;3</p>
        </footer>
      </div>

      {/* Video Modal */}
      {selectedJob && (
        <VideoModal
          job={selectedJob}
          onClose={() => setSelectedJob(null)}
        />
      )}
    </div>
  );
}

export default App;
