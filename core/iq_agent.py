import requests

class IQAgent:
    def __init__(self):
        print("[IQ] IQ AI Agent Initialized...")
        self.agent_url = "https://your-agent.iqai.com/api/chat"
        self.enabled   = True  # Set True after deploying your agent
        self.last_analysis = None

    def analyze(self, detections, threat_level, motion_score):
        if not self.enabled or not detections:
            return None

        # Build the payload to send to the Node.js IQ AI Bridge
        payload = {
            "threat_level": threat_level,
            "targets": len(detections),
            "motion_score": motion_score,
            "zones": list(set([d.get("zone", "UNKNOWN") for d in detections])),
            "distances": [d.get("distance", 0) for d in detections]
        }

        try:
            # Send data to our local Express server (which runs the IQ AI ADK)
            # URL will be our local bridge on port 3000
            bridge_url = "http://localhost:3000/analyze"
            
            response = requests.post(
                bridge_url,
                json=payload,
                timeout=5
            )
            
            result = response.json().get("response", "No response from Bridge")
            self.last_analysis = result
            return result
            
        except requests.exceptions.ConnectionError:
            return "IQ AI Bridge Offline (Is the Node server running?)"
        except Exception as e:
            return f"Bridge Error: {e}"