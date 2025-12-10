const express = require('express');
const { Client, LocalAuth } = require('whatsapp-web.js');
const OpenAI = require('openai');
const qrcode = require('qrcode-terminal');
const path = require('path');
const cors = require('cors');
require('dotenv').config({ path: path.join(__dirname, '../.env') });

const app = express();
const PORT = 3000;

app.use(express.json());
app.use(cors());

// --- Configuration ---
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const SYSTEM_PROMPT = "Eres el espíritu del Árbol Encantado. Tu misión es desear Feliz Navidad y traer magia a quienes te hablan. Responde de forma amable, mágica y concisa (máximo 2 frases). Si te preguntan quién eres, di que eres el guardián de la Navidad.";

if (!OPENAI_API_KEY) {
    console.warn("WARNING: OPENAI_API_KEY is missing via .env. Chatbot features will not work.");
}

const openai = OPENAI_API_KEY ? new OpenAI({ apiKey: OPENAI_API_KEY }) : null;

// --- WhatsApp Client Init ---
const puppeteerConfig = {
    headless: true,
    args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--disable-gpu'
    ]
};

// Check for system chromium on Linux (Raspberry Pi optimization)
const fs = require('fs');
if (process.platform === 'linux') {
    const possiblePaths = ['/usr/bin/chromium', '/usr/bin/chromium-browser'];
    for (const p of possiblePaths) {
        if (fs.existsSync(p)) {
            console.log(`Using system Chromium: ${p}`);
            puppeteerConfig.executablePath = p;
            break;
        }
    }
}

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: puppeteerConfig
});

// --- WhatsApp Events ---
client.on('qr', (qr) => {
    console.log('\nPlease scan the QR code to log in:');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('WhatsApp Client is READY!');
});

client.on('authenticated', () => {
    console.log('WhatsApp Authenticated successfully.');
});

client.on('auth_failure', payload => {
    console.error('Authentication failure:', payload);
});

// --- Chatbot Logic ---
client.on('message', async msg => {
    // Ignore status updates, self messages, or group messages (optional)
    if (msg.from.includes('status') || msg.fromMe) return;

    console.log(`Message received from ${msg.from}: ${msg.body}`);

    if (!openai) return;

    try {
        // Simple delay to make it feel natural
        await new Promise(r => setTimeout(r, 1000));

        // Show "typing..." state
        const chat = await msg.getChat();
        await chat.sendStateTyping();

        const response = await openai.chat.completions.create({
            model: "gpt-4o-mini", // Cost efficient and fast
            messages: [
                { role: "system", content: SYSTEM_PROMPT },
                { role: "user", content: msg.body }
            ],
            max_tokens: 150,
            temperature: 0.7
        });

        const replyText = response.choices[0].message.content;

        // Clear typing state not strictly necessary as sending message clears it, but good practice
        // await chat.clearStateTyping(); 

        console.log(`Replying: ${replyText}`);
        await msg.reply(replyText);

    } catch (error) {
        console.error("Error calling OpenAI or sending reply:", error);
    }
});


// --- Python API Endpoints ---

// Endpoint to send the welcome message
app.post('/send-welcome', async (req, res) => {
    const { phoneNumber } = req.body;

    if (!phoneNumber) {
        return res.status(400).json({ success: false, error: "phoneNumber is required" });
    }

    console.log(`API Request: Send welcome to ${phoneNumber}`);

    try {
        // Standardize format to ID
        // Assuming input is like "573001234567"
        let chatId = phoneNumber.replace(/\D/g, "") + "@c.us";

        // Check if number is registered (optional validation)
        const isRegistered = await client.isRegisteredUser(chatId);
        if (!isRegistered) {
            console.warn(`Number ${chatId} not registered on WhatsApp.`);
            // Try fallback for Mexico/Argentina widely known issue? 
            // For now, proceed or return error. Let's try to proceed as sometimes isRegistered is flaky.
        }

        const messageText = "¡Hola! Aquí tienes tu video del Árbol Encantado. ¡Feliz Navidad!";

        // Send
        await client.sendMessage(chatId, messageText);
        console.log(`Welcome message sent to ${chatId}`);

        res.json({ success: true, message: "Message sent successfully" });

    } catch (error) {
        console.error("Failed to send welcome message via API:", error);
        res.status(500).json({ success: false, error: error.message });
    }
});


// --- Start Server ---
app.listen(PORT, () => {
    console.log(`\n>>> Messaging Server running on http://localhost:${PORT}`);
    console.log(`>>> Initializing WhatsApp Client...`);
    client.initialize();
});
