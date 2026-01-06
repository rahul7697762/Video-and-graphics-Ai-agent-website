import { createClient } from '@/lib/supabase/server';
import { NextResponse } from 'next/server';
// Import the templates
import { REAL_ESTATE_WALKTHROUGH } from '@/lib/heygen/templates';

export async function POST(req: Request) {
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    try {
        const body = await req.json();
        const { propertyId, avatarId, voiceId, mediaUrls } = body;

        // 1. Fetch Property Details
        const { data: property, error: propError } = await supabase
            .from('video_properties')
            .select('*')
            .eq('id', propertyId)
            .single();

        if (propError || !property) throw new Error("Property not found");

        const details = property.details || {};

        // 2. Map Wizard Inputs to Template Keys
        // Wizard Keys: exterior, hall, kitchen, bedroom, balcony, amenities
        // Template Keys: exterior, entry, bedroom, kitchen, dining, balcony, cta
        const mediaMap: Record<string, string> = {
            'exterior': mediaUrls['exterior'],
            'entry': mediaUrls['hall'],
            'dining': mediaUrls['hall'], // Reuse hall for dining shot
            'kitchen': mediaUrls['kitchen'],
            'bedroom': mediaUrls['bedroom'],
            'balcony': mediaUrls['balcony'],
            'cta': mediaUrls['exterior'], // Reuse exterior for CTA/Outro
            'amenities': mediaUrls['amenities'] // Fallback if template adds it
        };

        // 3. Dynamic Text Processor
        // Replaces generic terms in template with specific Property Details
        const processScript = (text: string, data: any) => {
            let processed = text;

            // Basic Replacements
            processed = processed.replace(/3BHK/gi, data.propertyType || 'luxury');
            processed = processed.replace(/apartment/gi, 'home');
            processed = processed.replace(/Pune/gi, data.city || 'the city');

            // Contextual Replacements (Intro)
            if (text.includes('Welcome to')) {
                const intro = `Welcome to ${data.projectName}, a premium ${data.propertyType} in ${data.locality}, ${data.city}.`;
                // If template has generic intro, we replace it or prepend. 
                // For now, let's Replace the first sentence or just prepend if it's the Intro scene.
                return intro + " " + processed.replace('Welcome to this beautiful 3BHK apartment.', '');
            }

            // Amenities
            if (text.includes('amenities')) {
                const amenitiesList = data.amenities ?
                    data.amenities.split('|').filter((s: string) => s.includes(':Yes')).map((s: string) => s.split(':')[0]).join(', ')
                    : 'premium features';
                return processed + ` Enjoy ${amenitiesList}.`;
            }

            return processed;
        };

        // 4. Construct Video Inputs
        const videoInputs = REAL_ESTATE_WALKTHROUGH.map((scene) => {
            const finalText = processScript(scene.text, details);
            const imageUrl = mediaMap[scene.mediaKey];

            const input: any = {
                character: {
                    type: 'avatar',
                    avatar_id: avatarId,
                    scale: 1,
                    avatar_style: 'normal'
                },
                voice: {
                    type: 'text',
                    voice_id: voiceId || '1bd001e7e50f421d891986aad5158bc8', // Ensure valid voice
                    input_text: finalText
                }
            };

            // Add Background
            if (imageUrl) {
                input.background = {
                    type: 'image',
                    url: imageUrl,
                    fit: 'cover'
                };
            } else {
                // Fallback to Exterior if scene image missing
                const fallback = mediaUrls['exterior'];
                if (fallback) {
                    input.background = { type: 'image', url: fallback, fit: 'cover' };
                }
            }

            // Remove avatar if scene config says so
            if (!scene.hasAvatar) {
                delete input.character;
            }

            return input;
        });

        // 5. Call HeyGen API
        const res = await fetch('https://api.heygen.com/v2/video/generate', {
            method: 'POST',
            headers: {
                'X-Api-Key': process.env.HEYGEN_API_KEY!,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                video_inputs: videoInputs,
                dimension: { width: 1080, height: 1920 }, // 9:16 Vertical
                test: true
            }),
        });

        if (!res.ok) {
            const errText = await res.text();
            console.error('HeyGen API Error:', errText);
            throw new Error(`HeyGen API Error: ${errText}`);
        }

        const heygenResponse = await res.json();
        const heygenData = heygenResponse.data;

        if (!heygenData || !heygenData.video_id) {
            throw new Error('No video_id returned from HeyGen');
        }

        // Create Video Record
        const { data: video, error } = await supabase.from('videos').insert({
            user_id: user.id,
            property_id: propertyId,
            avatar_id: avatarId,
            voice_id: voiceId,
            script_content: "Dynamic Template Walkthrough",
            status: 'pending',
            heygen_video_id: heygenData.video_id,
            meta: { mediaUrls, template: 'REAL_ESTATE_WALKTHROUGH' }
        }).select().single();

        if (error) throw error;

        // Create Render Job
        await supabase.from('video_render_jobs').insert({
            video_id: video.id,
            heygen_job_id: heygenData.video_id,
            status: 'pending'
        });

        return NextResponse.json({ success: true, videoId: video.id });
    } catch (err: any) {
        console.error('Video Generation Error:', err);
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}
