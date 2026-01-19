import { createClient } from '@/lib/supabase/server';
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { id, status, url, metadata } = body;

    if (!id || !status) {
      return NextResponse.json({ error: 'Invalid payload' }, { status: 400 });
    }

    const supabase = createClient();
    
    // Parse metadata if it exists and is a string, otherwise use it as is if it's an object
    let parsedMetadata = metadata;
    if (typeof metadata === 'string') {
        try {
            parsedMetadata = JSON.parse(metadata);
        } catch (e) {
            console.warn('Failed to parse metadata string:', e);
        }
    }

    const videoId = parsedMetadata?.videoId;

    if (videoId) {
        // If we have our internal videoId, update based on that
        const updateData: any = {
            status: status === 'succeeded' ? 'completed' : status === 'failed' ? 'failed' : 'pending',
            video_url: url
        };
        
        // We also want to update the meta column with the creatomate info
        // First fetch current meta
        const { data: currentVideo } = await supabase.from('videos').select('meta').eq('id', videoId).single();
        
        if (currentVideo) {
             updateData.meta = {
                ...currentVideo.meta,
                creatomate_id: id,
                render_url: url,
                last_webhook_status: status
            };
        }

        const { error } = await supabase
            .from('videos')
            .update(updateData)
            .eq('id', videoId);

        if (error) {
            console.error('Database update failed:', error);
            throw error;
        }
    } else {
        // Fallback: try to find by creatomate_id in meta
        // This is harder with JSONB columns if not indexed properly for search, 
        // ideally we always pass videoId in metadata.
        console.warn('No videoId in metadata, attempting fallback or logging only.');
    }

    return NextResponse.json({ received: true });

  } catch (error: any) {
    console.error('Webhook Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
