const express = require('express');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const OpenAI = require('openai');
const QRCode = require('qrcode');
const qrcode = require('qrcode-terminal');
const path = require('path');
const cors = require('cors');
require('dotenv').config({ path: path.join(__dirname, '../.env') });

const app = express();
const PORT = 3000;

app.use(express.json());
app.use(cors());
// Serve static files to easily view QR if needed (optional)
app.use(express.static(path.join(__dirname, 'public')));

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
    authStrategy: new LocalAuth({ clientId: 'encantado_v3' }),
    puppeteer: puppeteerConfig,
    // webVersionCache: {
    //     type: 'remote',
    //     remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2407.3.html',
    // }
});

let isClientReady = false;

// --- WhatsApp Events ---
client.on('qr', (qr) => {
    console.log('\nPlease scan the QR code to log in:');
    qrcode.generate(qr, { small: true });

    // Save QR to file as well
    const qrPath = path.join(__dirname, 'qr_code.png');
    QRCode.toFile(qrPath, qr, (err) => {
        if (err) console.error('Error saving QR code image:', err);
        else console.log(`QR Code image saved to: ${qrPath}`);
    });
});

client.on('ready', () => {
    console.log('WhatsApp Client is READY!');
    isClientReady = true;
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
    const { phoneNumber, videoPath } = req.body;

    if (!isClientReady) {
        console.warn("API Request blocked: Client not ready yet.");
        return res.status(503).json({ success: false, error: "WhatsApp Client is not ready yet. Please wait a moment." });
    }

    if (!phoneNumber) {
        return res.status(400).json({ success: false, error: "phoneNumber is required" });
    }

    console.log(`API Request: Send welcome to ${phoneNumber} with video: ${videoPath}`);

    try {
        // Standardize format to ID
        // Assuming input is like "573001234567"
        let chatId = phoneNumber.replace(/\D/g, "") + "@c.us";

        // Check if number is registered (optional validation)
        let finalId = chatId;
        try {
            // Attempt to verify registration to avoid invalid ID errors
            const isRegistered = await client.isRegisteredUser(chatId);
            if (!isRegistered) {
                console.warn(`Number ${chatId} not registered on WhatsApp.`);
                // Still try to send, sometimes verification fails but sending works
            }
        } catch (verErr) {
            console.warn("Could not verify user registration, trying sending anyway...", verErr);
        }

        const messageText = "¡Hola! Aquí tienes tu video del Árbol Encantado. ¡Feliz Navidad!";

        let sentMsg;
        if (videoPath && require('fs').existsSync(videoPath)) {
            try {
                // Check file size first? 
                // For now, let's just try sending directly as requested.
                // If it fails (like the t:t error), it's likely size/encoding related.

                const media = MessageMedia.fromFilePath(videoPath);

                // Optional: Send as document if too large? 
                // client.sendMessage(finalId, media, { sendMediaAsDocument: true, caption: messageText });

                sentMsg = await client.sendMessage(finalId, media, { caption: messageText });
                console.log(`Video message sent to ${finalId}`);
            } catch (mediaErr) {
                console.error("Error attaching media, sending text only:", mediaErr);
                sentMsg = await client.sendMessage(finalId, messageText + "\n(No pudimos adjuntar el video, lo sentimos)");
            }
        } else {
            if (videoPath) console.warn(`Video path not found: ${videoPath}`);
            sentMsg = await client.sendMessage(finalId, messageText);
        }

        console.log(`Welcome message processing for ${finalId}. Waiting for server acknowledgement...`);

        // Wait for ACK to ensure delivery to server
        await new Promise((resolve) => {
            const timeout = setTimeout(() => {
                console.warn('Timeout waiting for ACK, but message request was sent to browser.');
                resolve();
            }, 10000); // Wait up to 10 seconds

            const ackListener = (msg, ack) => {
                if (msg.id._serialized === sentMsg.id._serialized) {
                    console.log(`ACK received: ${ack}`);
                    // ack 1 = sent to server, 2 = delivered, 3 = read
                    if (ack >= 1) {
                        clearTimeout(timeout);
                        client.removeListener('message_ack', ackListener); // Cleanup
                        console.log('Message successfully reached WhatsApp server.');
                        resolve();
                    }
                }
            };

            client.on('message_ack', ackListener);
        });

        console.log(`Verified processing for ${finalId} completed.`);

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
