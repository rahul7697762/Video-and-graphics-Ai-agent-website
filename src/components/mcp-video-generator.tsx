'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Loader2, Play, Video, AlertCircle, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';

type Status = 'idle' | 'generating' | 'completed' | 'error';

export default function MCPVideoGenerator() {
    const [prompt, setPrompt] = useState('');
    const [status, setStatus] = useState<Status>('idle');
    const [result, setResult] = useState('');
    const [videoUrl, setVideoUrl] = useState('');

    const handleGenerate = async () => {
        if (!prompt.trim()) {
            toast.error('Please enter a prompt');
            return;
        }

        setStatus('generating');
        setResult('');
        setVideoUrl('');

        try {
            const response = await fetch('/api/mcp/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Generation failed');
            }

            setResult(data.result || 'Video generation started');

            // If the result contains a URL, extract it
            const urlMatch = data.result?.match(/https?:\/\/[^\s]+/);
            if (urlMatch) {
                setVideoUrl(urlMatch[0]);
            }

            setStatus('completed');
            toast.success('Video generated successfully!');

        } catch (error: any) {
            console.error('MCP Generation Error:', error);
            setResult(error.message);
            setStatus('error');
            toast.error(error.message);
        }
    };

    return (
        <div className="max-w-2xl mx-auto p-8 bg-card rounded-xl shadow-lg border my-10">
            <div className="flex items-center gap-3 mb-6">
                <div className="p-3 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl">
                    <Video className="h-6 w-6 text-white" />
                </div>
                <div>
                    <h2 className="text-2xl font-bold tracking-tight">AI Video Creator</h2>
                    <p className="text-sm text-muted-foreground">Powered by Creatomate MCP</p>
                </div>
            </div>

            <div className="space-y-4">
                <textarea
                    className="w-full p-4 border rounded-lg min-h-[120px] bg-background resize-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                    placeholder="Describe your video...

Example: Create a vertical 9:16 real estate promo with modern transitions, showing a luxury apartment with price overlay '₹1.2 Cr' and location badge 'Mumbai, India'."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    disabled={status === 'generating'}
                />

                <Button
                    onClick={handleGenerate}
                    disabled={status === 'generating' || !prompt.trim()}
                    className="w-full gap-2 h-12 text-base"
                    size="lg"
                >
                    {status === 'generating' ? (
                        <>
                            <Loader2 className="h-5 w-5 animate-spin" />
                            Generating Video...
                        </>
                    ) : (
                        <>
                            <Play className="h-5 w-5" />
                            Generate Video
                        </>
                    )}
                </Button>
            </div>

            {/* Result Display */}
            {(status === 'completed' || status === 'error') && (
                <div className={`mt-6 p-4 rounded-lg border ${status === 'error' ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'}`}>
                    <div className="flex items-start gap-3">
                        {status === 'error' ? (
                            <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
                        ) : (
                            <CheckCircle2 className="h-5 w-5 text-green-500 mt-0.5" />
                        )}
                        <div className="flex-1">
                            <p className={`font-medium ${status === 'error' ? 'text-red-700' : 'text-green-700'}`}>
                                {status === 'error' ? 'Generation Failed' : 'Generation Complete'}
                            </p>
                            <p className="text-sm text-muted-foreground mt-1 break-all">{result}</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Video Preview */}
            {videoUrl && (
                <div className="mt-6">
                    <h3 className="font-semibold mb-2">Video Preview</h3>
                    <div className="relative aspect-[9/16] max-w-[300px] mx-auto rounded-xl overflow-hidden shadow-xl border">
                        <video
                            src={videoUrl}
                            controls
                            className="w-full h-full object-cover"
                        />
                    </div>
                </div>
            )}
        </div>
    );
}
