import { useState, useEffect } from 'react';
import { createClient } from '@/lib/supabase/client';

export function useVideoStatus(videoId: string) {
    const [video, setVideo] = useState<any>(null);
    const [status, setStatus] = useState<string>('pending');
    const supabase = createClient();

    useEffect(() => {
        if (!videoId) return;

        const fetchStatus = async () => {
            const { data } = await supabase
                .from('videos')
                .select('*')
                .eq('id', videoId)
                .single();

            if (data) {
                setVideo(data);
                setStatus(data.status || 'pending');
            }
        };

        fetchStatus();
        const interval = setInterval(fetchStatus, 3000); // Poll every 3s

        return () => clearInterval(interval);
    }, [videoId]);

    return { status, video };
}
