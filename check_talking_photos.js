const https = require('https');

const API_KEY = 'sk_V2_hgu_kvV9z5c7rWL_8fBz9THp48BwxWMvMTZd4Zz3S6CCW9LF';

const options = {
    hostname: 'api.heygen.com',
    path: '/v2/talking_photos',
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
            if (json.error) {
                console.log('Error fetching talking photos:', json.error);
                return;
            }

            const photos = json.data.talking_photos || [];
            console.log(`Talking Photos Found: ${photos.length}`);

            if (photos.length > 0) {
                console.log(JSON.stringify(photos.slice(0, 3), null, 2));
            } else {
                console.log("No talking photos found.");
            }

        } catch (e) {
            console.error('Error:', e.message);
        }
    });
});

req.end();
