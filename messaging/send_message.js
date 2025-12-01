const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        args: ['--no-sandbox']
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
