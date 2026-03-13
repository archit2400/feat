import requests

class IQAgent:
    def __init__(self):
        print("[IQ] IQ AI Agent Initialized...")
        self.agent_url = "https://your-agent.iqai.com/api/chat"
        self.enabled   = False  # Set True after deploying your agent
        self.last_analysis = None

    def analyze(self, detections, threat_level, motion_score):
        if not self.enabled or not detections:
            return None

        prompt = (
            f"FEAT Edge Node Tactical Report:\n"
            f"Threat Level: {threat_level}\n"
            f"Targets: {len(detections)}\n"
            f"Motion Score: {motion_score}\n"
            f"Zones Active: {[d['zone'] for d in detections]}\n"
            f"Distances: {[str(d['distance'])+'m' for d in detections]}\n\n"
            f"You are a tactical AI. Give:\n"
            f"1. Threat assessment (1 line)\n"
            f"2. Action (1 line)\n"
            f"3. Risk: LOW/MEDIUM/HIGH/CRITICAL"
        )

        try:
            response = requests.post(
                self.agent_url,
                json={"messages": [{"role": "user", "content": prompt}]},
                timeout=5
            )
            result = response.json().get("response", "No response")
            self.last_analysis = result
            return result
        except Exception as e:
            return f"Agent offline: {e}"