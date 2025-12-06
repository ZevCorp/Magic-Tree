const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const fs = require('fs');

let puppeteerConfig = {
    args: ['--no-sandbox', '--disable-setuid-sandbox']
};

// Check for system Chromium (common on Raspberry Pi)
const possiblePaths = [
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome-stable',
    '/snap/bin/chromium'
];

let foundPath = null;
for (const path of possiblePaths) {
    if (fs.existsSync(path)) {
        foundPath = path;
        break;
    }
}

if (process.platform === 'linux' && foundPath) {
    console.log(`Using system Chromium at ${foundPath}`);
    puppeteerConfig.executablePath = foundPath;
}

// Add robust args for environment
puppeteerConfig.args = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-accelerated-2d-canvas',
    '--disable-gpu'
];

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: puppeteerConfig,
    webVersionCache: {
        type: 'remote',
        remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html',
    }
});

const args = process.argv.slice(2);
const phoneNumber = args[0]; // Format: 5215512345678 (Country code + number)
const message = "¡Hola! Aquí tienes tu video del Árbol Encantado. ¡Feliz Navidad!";

if (process.argv.includes('--auth')) {
    console.log('Starting in Auth mode...');
}

client.on('qr', (qr) => {
    console.log('QR RECEIVED', qr);
    qrcode.generate(qr, { small: true });
});

client.on('ready', async () => {
    console.log('Client is ready!');

    // Wait a bit for the interface to stabilize
    console.log('Waiting 10 seconds for WhatsApp Web to stabilize...');
    await new Promise(resolve => setTimeout(resolve, 10000));

    if (phoneNumber) {
        // Format number: remove non-digits, ensure suffix
        let chatId = phoneNumber.replace(/\D/g, '') + "@c.us";

        try {
            // Attempt to resolve the correct ID (handles LIDs and format issues)
            let numberDetails = null;
            try {
                numberDetails = await client.getNumberId(chatId);
            } catch (e) {
                console.warn('getNumberId failed (likely invalid format or WWebJS error), trying direct send...', e.message);
            }

            // Fallback for Mexico: if 521 fails, try 52
            if (!numberDetails && chatId.startsWith('521')) {
                const altId = chatId.replace('521', '52');
                console.log(`Retrying with alternative ID: ${altId}`);
                try {
                    numberDetails = await client.getNumberId(altId);
                } catch (e) {
                    console.warn('Alternative getNumberId failed:', e.message);
                }
            }

            // If resolution worked, use the serialized ID. If not, fallback to original chatId.
            const finalId = numberDetails ? numberDetails._serialized : chatId;

            console.log(`Attempting to send to: ${finalId}`);
            const sentMsg = await client.sendMessage(finalId, message);
            console.log(`Message sent to ${finalId}. Waiting for server acknowledgement...`);

            // Wait for ACK to ensure delivery to server
            const ackPromise = new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    console.warn('Timeout waiting for ACK, but message request was sent.');
                    resolve(); // Resolve anyway to not block forever, but log warning
                }, 30000);

                client.on('message_ack', (msg, ack) => {
                    if (msg.id._serialized === sentMsg.id._serialized) {
                        console.log(`ACK received: ${ack}`);
                        if (ack >= 1) {
                            clearTimeout(timeout);
                            console.log('Message successfully reached WhatsApp server.');
                            resolve();
                        }
                    }
                });
            });

            await ackPromise;
            console.log('Exiting...');
            process.exit(0);

        } catch (err) {
            console.error('Failed to send message:', err);
            process.exit(1);
        }
    } else {
        if (!process.argv.includes('--auth')) {
            console.log('No phone number provided. Use --auth to just authenticate.');
            process.exit(0);
        }
    }
});

client.on('auth_failure', msg => {
    console.error('AUTHENTICATION FAILURE', msg);
    process.exit(1);
});

client.initialize().catch(err => {
    console.error('Initialization failed:', err.message);
    if (err.message.includes('SingletonLock') || err.message.includes('File exists')) {
        console.error('\nPOSSIBLE FIX: A previous Chrome session is still locked.');
        console.error('Try running the following commands to clear the lock:');
        console.error('  pkill -f chromium');
        console.error('  rm -rf .wwebjs_auth/session/SingletonLock');
    }
    process.exit(1);
});
