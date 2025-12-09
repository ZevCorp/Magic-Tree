const { Client, LocalAuth } = require('whatsapp-web.js');
const OpenAI = require('openai');
const qrcode = require('qrcode-terminal');
const fs = require('fs');
const path = require('path');

// OpenAI Config
// Try to get key from env or config file, fallback to placeholder
let OPENAI_API_KEY = process.env.OPENAI_API_KEY;

// Simple hardcoded fallback for demo if env missing (Not recommended for prod)
// In a real scenario, we'd pass this via process.env or read a .env file
if (!OPENAI_API_KEY) {
    console.warn("OPENAI_API_KEY not found in environment. Bot will fail to reply.");
}

const openai = new OpenAI({
    apiKey: OPENAI_API_KEY,
});

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

client.on('qr', (qr) => {
    console.log('QR RECEIVED', qr);
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('WhatsApp Bot is ready!');
});

client.on('message', async msg => {
    console.log(`Received message from ${msg.from}: ${msg.body}`);

    // Ignore self or status messages
    if (msg.from.includes('status') || msg.fromMe) return;

    try {
        const response = await openai.chat.completions.create({
            model: "gpt-4o-mini",
            messages: [
                { role: "system", content: "Eres un asistente amable del 'Árbol Encantado'. Responde de forma concisa y mágica." },
                { role: "user", content: msg.body }
            ],
            max_tokens: 150
        });

        const replyText = response.choices[0].message.content;
        console.log(`Replying: ${replyText}`);
        msg.reply(replyText);

    } catch (error) {
        console.error("OpenAI Error:", error);
    }
});

client.initialize();
