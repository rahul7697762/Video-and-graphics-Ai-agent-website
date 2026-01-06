const HEYGEN_API_URL = 'https://api.heygen.com/v2';
const HEYGEN_API_KEY = process.env.HEYGEN_API_KEY;
const avatar_id = "Abigail_expressive_2024112501";
const voice_id = "97dd67ab8ce242b6a9e7689cb00c6414";


export async function getAvatars() {
    const res = await fetch(`${HEYGEN_API_URL}/avatars`, {
        headers: {
            'X-Api-Key': HEYGEN_API_KEY!,
        },
    });
    if (!res.ok) throw new Error('Failed to fetch avatars');
    return res.json();
}


export async function getVoices() {
    const res = await fetch(`${HEYGEN_API_URL}/voices`, {
        headers: {
            'X-Api-Key': HEYGEN_API_KEY!,
        },
    });
    if (!res.ok) throw new Error('Failed to fetch voices');
    return res.json();
}

export async function generateVideo(script: string) {
    const res = await fetch(`${HEYGEN_API_URL}/video/generate`, {
        method: 'POST',
        headers: {
            'X-Api-Key': HEYGEN_API_KEY!,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            video_inputs: [
                {
                    character: {
                        type: 'avatar',
                        avatar_id: avatar_id,
                        scale: 1,
                        avatar_style: 'normal'
                    },
                    voice: {
                        type: 'text',
                        input_text: script,
                        voice_id: voice_id
                    }
                }
            ],
            dimension: { width: 1920, height: 1080 }
        }),
    });

    if (!res.ok) {
        const error = await res.text();
        throw new Error(`HeyGen API Error: ${error}`);
    }

    return res.json();
}
