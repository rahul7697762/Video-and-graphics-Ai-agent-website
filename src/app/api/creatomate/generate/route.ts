
import { createClient } from '@/lib/supabase/server';
import { NextResponse } from 'next/server';
import { videoTemplate } from './template';

export async function POST(req: Request) {
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    try {
        const body = await req.json();
        const { modifications, propertyId } = body;

        const apiKey = 'cd3c32746bf2461caa3b411b77263cf9386411e60c6a56974dc25a984ad50872b4486f3e706d31d2ff3e3147e56aa662';
        const templateId = '6ac80fd5-c928-4640-ac1c-c3a0bafac3c5';
        const url = 'https://api.creatomate.com/v2/renders';

        // 1. Create Initial Video Record
        const { data: video, error: dbError } = await supabase.from('videos').insert({
            user_id: user.id,
            property_id: propertyId,
            status: 'pending', // Creatomate is async
            script_content: 'Creatomate Video Edit',
            meta: { template: 'CREATOMATE_EDIT', modifications }
        }).select().single();

        if (dbError) throw dbError;

        const data = {
            template_id: templateId,
            modifications: modifications,
            // Tagging for potential webhook correlation if needed later
            metadata: JSON.stringify({ videoId: video.id, userId: user.id })
        };

        const maxRetries = 3;
        let response;
        let lastError;

        for (let i = 0; i < maxRetries; i++) {
            try {
                if (i > 0) {
                    await new Promise(resolve => setTimeout(resolve, 500 * Math.pow(2, i - 1)));
                }

                response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${apiKey}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data),
                    cache: 'no-store'
                });

                if (response.ok) break;

                if (response.status < 500) {
                    const result = await response.json();
                    throw new Error(result.error || `Request failed with status ${response.status}`);
                }
            } catch (err: any) {
                console.warn(`Attempt ${i + 1} failed:`, err.message);
                lastError = err;
            }
        }

        if (!response || !response.ok) {
            throw lastError || new Error('Failed to connect to Creatomate API');
        }

        const result = await response.json();
        const render = Array.isArray(result) ? result[0] : result;

        if (render) {
            // Update video with Creatomate details
            await supabase.from('videos').update({
                meta: {
                    ...video.meta,
                    creatomate_id: render.id,
                    render_url: render.url
                },
                // If the URL is provided, we use it. Even if it returns 404 initially, it's the valid URL.
                // We leave status as 'pending' mostly, unless it says 'succeeded'.
                status: render.status === 'succeeded' ? 'completed' : 'pending',
                video_url: render.url // Optimistically save the URL
            }).eq('id', video.id);
        }

        return NextResponse.json({ success: true, videoId: video.id });

    } catch (error: any) {
        console.error('Creatomate Error:', error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
