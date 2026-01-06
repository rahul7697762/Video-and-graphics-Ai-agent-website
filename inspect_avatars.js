const https = require('https');
const fs = require('fs');

const API_KEY = 'sk_V2_hgu_kvV9z5c7rWL_8fBz9THp48BwxWMvMTZd4Zz3S6CCW9LF';

const options = {
    hostname: 'api.heygen.com',
    path: '/v2/avatars',
    method: 'GET',
    headers: {
        'X-Api-Key': API_KEY,
        'Content-Type': 'application/json'
    }
};

const req = https.request(options, (res) => {
    let data = '';

    res.on('data', (chunk) => {
        data += chunk;
    });

    res.on('end', () => {
        try {
            const json = JSON.parse(data);
            const avatars = json.data.avatars || [];

            // Bucket avatars by keys present
            const keys = new Set();
            avatars.forEach(a => Object.keys(a).forEach(k => keys.add(k)));
            console.log('All available keys:', Array.from(keys));

            // Check for any specific custom indicators
            const withType = avatars.filter(a => a.type !== null && a.type !== undefined);
            console.log(`Avatars with non-null type: ${withType.length}`);
            if (withType.length > 0) {
                console.log('Sample with type:', JSON.stringify(withType[0], null, 2));
            }

            const withTags = avatars.filter(a => a.tags !== null && a.tags !== undefined);
            console.log(`Avatars with tags: ${withTags.length}`);

            // Check for 'premium' flag
            const premium = avatars.filter(a => a.premium === true);
            console.log(`Premium Avatars: ${premium.length}`);

            // Try to find if there is an "avatar_group_id" or similar
            // Save 5 random avatars to file for me to read
            fs.writeFileSync('avatar_samples.json', JSON.stringify(avatars.slice(0, 5), null, 2));

            // Also save the LAST 5, maybe custom ones are at the end?
            fs.writeFileSync('avatar_samples_end.json', JSON.stringify(avatars.slice(-5), null, 2));

        } catch (e) {
            console.error('Error:', e.message);
        }
    });
});

req.end();
