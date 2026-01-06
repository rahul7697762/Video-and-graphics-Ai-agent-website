const https = require('https');

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
            console.log(`Total Avatars: ${avatars.length}`);

            // Group by 'type' or check for 'is_custom' or similar fields
            const types = {};
            avatars.forEach(a => {
                const t = a.type || 'undefined';
                types[t] = (types[t] || 0) + 1;
            });
            console.log('Avatar Types Distribution:', types);

            // Print a few examples of potential custom avatars
            // Often custom avatars might have type 'talking_photo' or specific tags
            const potentialCustom = avatars.filter(a => a.type !== 'avatar' || a.avatar_id.startsWith('c_') || a.is_custom);

            console.log('\nPotential Custom Avatars (First 5):');
            console.log(JSON.stringify(potentialCustom.slice(0, 5), null, 2));

            // Dump one standard avatar for comparison
            console.log('\nStandard Avatar Example:');
            console.log(JSON.stringify(avatars[0], null, 2));

        } catch (e) {
            console.error('Error:', e.message);
        }
    });
});

req.end();
