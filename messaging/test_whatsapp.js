const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const fs = require('fs');

// --- Configuration ---
const puppeteerConfig = {
    args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--disable-gpu'
    ]
};

// Check for system Chromium
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
    console.log(`[TEST] Using system Chromium at ${foundPath}`);
    puppeteerConfig.executablePath = foundPath;
}

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: puppeteerConfig,
    webVersionCache: {
        type: 'remote',
        remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html',
    }
});

const args = process.argv.slice(2);
const phoneNumber = args[0];

if (!phoneNumber) {
    console.error('Usage: node test_whatsapp.js <phone_number>');
    process.exit(1);
}

console.log(`[TEST] Starting WhatsApp Client to test number: ${phoneNumber}`);

client.on('qr', (qr) => {
    console.log('[TEST] QR RECEIVED', qr);
    qrcode.generate(qr, { small: true });
});

client.on('ready', async () => {
    console.log('[TEST] Client is ready!');
    console.log('[TEST] Waiting 5 seconds for stabilization...');
    await new Promise(resolve => setTimeout(resolve, 5000));

    // 1. Format Number
    let chatId = phoneNumber.replace(/\D/g, '') + "@c.us";
    console.log(`[TEST] Initial Chat ID: ${chatId}`);

    try {
        // 2. Resolve Number ID
        console.log('[TEST] Resolving number ID...');
        let numberDetails = await client.getNumberId(chatId);

        if (!numberDetails && chatId.startsWith('521')) {
            console.log('[TEST] Standard resolution failed. Trying Mexico fallback (52)...');
            const altId = chatId.replace('521', '52');
            numberDetails = await client.getNumberId(altId);
        }

        if (numberDetails) {
            console.log('[TEST] Number RESOLVED successfully:', numberDetails);
            const finalId = numberDetails._serialized;

            // 3. Send Message
            console.log(`[TEST] Sending message to: ${finalId}`);
            const msg = await client.sendMessage(finalId, "🧪 Test Message from Magic Tree Debugger");
            console.log('[TEST] Message object created. ID:', msg.id._serialized);

            // 4. Wait for ACK
            console.log('[TEST] Waiting for ACK (Delivery confirmation)...');
            let ackReceived = false;

            // Timeout for ACK
            setTimeout(() => {
                if (!ackReceived) {
                    console.error('[TEST] TIMEOUT: No ACK received after 30 seconds.');
                    process.exit(1);
                }
            }, 30000);

        } else {
            console.error(`[TEST] FAILED: Number ${chatId} is not registered on WhatsApp.`);
            process.exit(1);
        }

    } catch (err) {
        console.error('[TEST] ERROR:', err);
        process.exit(1);
    }
});

client.on('message_ack', (msg, ack) => {
    /*
        ACK_ERROR: -1
        ACK_PENDING: 0
        ACK_SERVER: 1
        ACK_DEVICE: 2
        ACK_READ: 3
        ACK_PLAYED: 4
    */
    console.log(`[TEST] ACK Received: ${ack} for message ${msg.id._serialized}`);
    if (ack >= 1) {
        console.log('[TEST] SUCCESS: Message reached server (ACK 1) or device (ACK 2).');
        process.exit(0);
    }
});

client.on('auth_failure', msg => {
    console.error('[TEST] AUTHENTICATION FAILURE', msg);
    process.exit(1);
});

client.initialize();
