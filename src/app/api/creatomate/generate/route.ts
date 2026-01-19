import { createClient } from '@/lib/supabase/server';
import { NextResponse } from 'next/server';
import { TemplateManager } from '@/lib/creatomate/template-manager';

export async function POST(req: Request) {
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    try {
        const body = await req.json();
        let { modifications, propertyId, templateId, data: templateData } = body;

        // Dynamic Template Logic
        if (templateId) {
            const manager = new TemplateManager();
            const template = manager.getTemplate(templateId);

            if (!template) {
                return NextResponse.json({ error: `Template '${templateId}' not found` }, { status: 404 });
            }

            // Apply template mapping
            modifications = manager.applyTemplate(template, templateData || {});

            // Also override the actual Creatomate Template ID from the config
            // Note: In strict mode, we might want to separate the 'Registry ID' from 'Creatomate ID'
            // For now, let's assume the config has the correct ID.
        }

        const apiKey = process.env.CREATOMATE_API_KEY;
        if (!apiKey) throw new Error("Missing CREATOMATE_API_KEY");

        // Default ID if not dynamic, OR overridden by template config if we loaded one 
        // We need to fetch the ID from the template config if available
        let creatomateTemplateId = '6ac80fd5-c928-4640-ac1c-c3a0bafac3c5'; // Default fallback

        if (templateId) {
            const manager = new TemplateManager();
            const template = manager.getTemplate(templateId);
            if (template?.id) creatomateTemplateId = template.id;
        }

        const url = 'https://api.creatomate.com/v2/renders';

        // 1. Create Initial Video Record
        const { data: video, error: dbError } = await supabase.from('videos').insert({
            user_id: user.id,
            property_id: propertyId,
            status: 'pending', // Creatomate is async
            script_content: templateId ? `Template: ${templateId}` : 'Creatomate Video Edit',
            meta: { template: 'CREATOMATE_EDIT', modifications, templateId }
        }).select().single();

        if (dbError) throw dbError;

        const data = {
            template_id: creatomateTemplateId,
            modifications: modifications,
            // Tagging for potential webhook correlation if needed later
            metadata: JSON.stringify({ videoId: video.id, userId: user.id }),
            webhook_url: `${req.headers.get('origin') || process.env.NEXT_PUBLIC_APP_URL}/api/creatomate/webhook`
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
