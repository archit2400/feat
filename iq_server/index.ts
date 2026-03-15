const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');

dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

app.post('/analyze', async (req, res) => {
    try {
        const { threat_level, targets, motion_score, zones, distances, weapons } = req.body;

        console.log(`\n🚨 Received Threat Alert from Python Node!`);
        console.log(`Threat Level: ${threat_level}`);
        console.log(`Targets: ${targets}`);
        console.log(`Distances: ${distances}`);
        console.log(`Zones Active: ${zones}`);

        let assessment = "Routine monitoring.";
        let action = "Continue scan.";
        let risk = "LOW";

        // Logic for determining High/Critical Risk!
        
        let has_proximity = false;
        if (distances && distances.length > 0) {
            has_proximity = Math.min(...distances) < 3.0; // Someone is closer than 3 meters
        }

        if (threat_level >= 80) {
            assessment = `CRITICAL THREAT: Armed or hostile target in ${zones.join(', ')}.`;
            action = "ENGAGE PROTOCOLS. Logging Event to Blockchain...";
            risk = "CRITICAL";
        } else if (threat_level >= 50 || has_proximity) {
            assessment = "ELEVATED RISK: Target breached 3-meter proximity.";
            action = "Monitoring closely. Prepare warning.";
            risk = "HIGH";
        } else if (threat_level >= 20 || motion_score > 50) {
            assessment = `POTENTIAL ANOMALY: Movement detected in ${zones.join(', ')}.`;
            action = "MAINTAIN OBSERVATION.";
            risk = "MEDIUM";
        }

        const iqResponse = `1. ${assessment}\n2. ${action}\n3. Risk: ${risk}`;

        console.log(`🤖 Agent Response: ${iqResponse}`);

        res.json({ response: iqResponse });
    } catch (error) {
        console.error("Error processing request:", error);
        res.status(500).json({ error: "Internal Server Error" });
    }
});

app.listen(port, () => {
    console.log(`🛡️  IQ AI Bridge Server running on http://localhost:${port}`);
    console.log(`Waiting for Python Edge Node telemetry...`);
});
