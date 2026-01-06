"use client"

import { useVideoStatus } from '@/hooks/use-video-status';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';
import Link from 'next/link';

export default function VideoDetailsPage({ params }: { params: { id: string } }) {
    const { status, video } = useVideoStatus(params.id);

    return (
        <div className="p-6 max-w-4xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold tracking-tight">Video Generation</h1>
                <Link href="/dashboard">
                    <Button variant="outline">Back to Dashboard</Button>
                </Link>
            </div>

            <div className="border rounded-xl p-8 bg-black/5 flex flex-col items-center justify-center min-h-[600px] relative overflow-hidden">
                {status === 'completed' ? (
                    <div className="flex flex-col items-center w-full animate-in zoom-in-50 duration-500">
                        <div className="relative w-full max-w-[340px] aspect-[9/16] rounded-xl overflow-hidden shadow-2xl border-4 border-white/20">
                            <iframe
                                // Assuming heygen_video_id allows embed or we have a URL column
                                // For HeyGen V2, direct embed might need specific URL pattern or check API.
                                // Ideally: video.video_url
                                src={video?.video_url || `https://app.heygen.com/embed/${video?.heygen_video_id}`}
                                className="w-full h-full"
                                allowFullScreen
                            />
                        </div>
                        <div className="mt-8 flex gap-4">
                            <Button className="gap-2">
                                <Download className="w-4 h-4" /> Download Video
                            </Button>
                            <Link href="/properties/new">
                                <Button variant="secondary">Create Another</Button>
                            </Link>
                        </div>
                    </div>
                ) : (
                    <div className="relative w-full max-w-[340px] aspect-[9/16] bg-slate-900 rounded-xl overflow-hidden shadow-2xl border border-slate-700">
                        {/* Background Image Placeholder */}
                        {video?.meta?.mediaUrls?.exterior && (
                            <img
                                src={video.meta.mediaUrls.exterior}
                                className="absolute inset-0 w-full h-full object-cover opacity-40 blur-[2px]"
                                alt="Preview"
                            />
                        )}

                        {/* Scanner Overlay */}
                        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center">
                            {/* The Scan Line */}
                            <div className="w-full h-[2px] bg-cyan-400 shadow-[0_0_20px_rgba(34,211,238,1)] animate-scanner absolute top-0" />

                            {/* Tech UI Elements */}
                            <div className="absolute top-4 right-4 text-[10px] grid gap-1 text-cyan-500/50 font-mono">
                                <div>SCENE_ID: {video?.id?.slice(0, 8)}</div>
                                <div>MODE: RENDER</div>
                                <div>FPS: 60</div>
                            </div>

                            <div className="mt-32 p-4 bg-black/60 backdrop-blur-md rounded-lg border border-cyan-500/30 text-center">
                                <div className="text-cyan-400 font-mono text-xs tracking-[0.2em] animate-pulse mb-1">
                                    SYSTEM PROCESSING
                                </div>
                                <div className="text-white font-bold text-lg">
                                    GENERATING SCENES
                                </div>
                                <p className="text-slate-400 text-xs mt-2 max-w-[200px]">
                                    {video?.meta?.template === 'CREATOMATE_EDIT'
                                        ? 'Rendering video edit. This may take a minute...'
                                        : 'Analyzing property details and synthesizing avatar script...'}
                                </p>
                                {video?.meta?.template === 'CREATOMATE_EDIT' && (
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="mt-4 border-cyan-500/50 text-cyan-400 hover:bg-cyan-950/30"
                                        onClick={() => window.location.reload()}
                                    >
                                        Check Status
                                    </Button>
                                )}
                            </div>
                        </div>

                        {/* Status Footer */}
                        <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black via-black/80 to-transparent">
                            <div className="flex justify-between text-[10px] text-cyan-500 font-mono uppercase">
                                <span>Status: {status}</span>
                                <span>
                                    {video?.heygen_video_id ? 'ID: HEYGEN' :
                                        video?.meta?.creatomate_id ? 'ID: CREATOMATE' : 'ID: PENDING'}
                                </span>
                            </div>
                            {/* Fake Progress Bar */}
                            <div className="w-full h-1 bg-slate-800 rounded-full mt-2 overflow-hidden">
                                <div className="h-full bg-cyan-500 animate-progress origin-left w-full" />
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <style jsx global>{`
        @keyframes scanner {
          0% { top: 0%; opacity: 0; }
          10% { opacity: 1; }
          90% { opacity: 1; }
          100% { top: 100%; opacity: 0; }
        }
        .animate-scanner {
            animation: scanner 3s linear infinite;
        }
        @keyframes progress {
            0% { transform: scaleX(0); }
            100% { transform: scaleX(1); }
        }
        .animate-progress {
            animation: progress 30s cubic-bezier(0.4, 0, 0.2, 1); // Mock 30s progress
        }
      `}</style>
        </div>
    );
}
