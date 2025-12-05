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
    '--no-first-run',
    '--no-zygote',
    '--single-process',
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

    if (phoneNumber) {
        // Format number: remove non-digits, ensure suffix
        let chatId = phoneNumber.replace(/\D/g, '') + "@c.us";

        try {
            await client.sendMessage(chatId, message);
            console.log(`Message sent to ${chatId}`);
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

client.initialize();
