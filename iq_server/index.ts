const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const { GoogleGenerativeAI } = require('@google/generative-ai');

dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// Initialize Gemini
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
let chatSession: any = null;

async function initChat() {
    try {
        const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });
        chatSession = model.startChat({
            history: [
                {
                    role: "user",
                    parts: [{ text: "You are the Tactical Brain of Project FEAT, a smart edge-native visor. You will receive telemetry data. You must ALWAYS respond in exactly 3 lines: \n1. [Assessment of the situation]\n2. [Tactical Action to take]\n3. Risk: [LOW, MEDIUM, HIGH, or CRITICAL]\nDo not add any Markdown formatting or extra text. Be concise, militaristic, and focus on survival directives." }],
                },
                {
                    role: "model",
                    parts: [{ text: "1. Acknowledged. Telemetry processing initialized.\n2. Awaiting first telemetry burst.\n3. Risk: UNKNOWN" }],
                }
            ]
        });
        console.log("🦾 Gemini AI initialized in Tactical Mode.");
    } catch (e) {
        console.error("Failed to initialize Gemini AI:", e);
    }
}

initChat();

app.post('/analyze', async (req: any, res: any) => {
    try {
        const { threat_level, targets, labels, motion_score, zones, distances } = req.body;

        console.log(`\n🚨 Received Threat Alert from Python Node!`);
        console.log(`Threat Level: ${threat_level}`);
        console.log(`Targets: ${targets} (${labels ? labels.join(', ') : 'unknown'})`);
        console.log(`Distances: ${distances}`);
        console.log(`Zones Active: ${zones}`);
        console.log(`Motion Score: ${motion_score}`);

        if (!chatSession) {
            await initChat();
        }

        const prompt = `Current Telemetry:
- Threat Level Score: ${threat_level}
- Target Count: ${targets}
- Detected Objects: ${labels ? labels.join(', ') : 'none'}
- Movement/Motion Score: ${motion_score}
- Active Zones: ${zones ? zones.join(', ') : 'none'}
- Distances (meters): ${distances ? distances.join(', ') : 'none'}

Provide tactical analysis.`;

        if (chatSession) {
            const result = await chatSession.sendMessage(prompt);
            const iqResponse = result.response.text().trim();
            console.log(`🤖 Agent Response:\n${iqResponse}`);
            res.json({ response: iqResponse });
        } else {
            // Fallback
            res.json({ response: "1. API Offline\n2. Maintain visual.\n3. Risk: UNKNOWN" });
        }

    } catch (error) {
        console.error("Error processing request:", error);
        res.status(500).json({ error: "Internal Server Error" });
    }
});

app.listen(port, () => {
    console.log(`🛡️  IQ AI Bridge Server running on http://localhost:${port}`);
    console.log(`Waiting for Python Edge Node telemetry...`);
});
