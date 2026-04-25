from typing import Dict


class LocalRouter:
    """Privacy-first local routing policy."""

    def __init__(self, sensitive_keywords):
        self.sensitive_keywords = [k.lower() for k in sensitive_keywords]

    def analyze_privacy(self, prompt: str, requested_level: str) -> Dict:
        prompt_lower = prompt.lower()
        matched = [k for k in self.sensitive_keywords if k in prompt_lower]
        if requested_level == "sensitive" or matched:
            return {
                "privacy_level": "sensitive",
                "confidence": 0.95 if matched else 1.0,
                "sensitive_elements": matched,
                "recommendation": "Route locally",
            }
        if requested_level == "private":
            return {
                "privacy_level": "private",
                "confidence": 1.0,
                "sensitive_elements": [],
                "recommendation": "Prefer local route",
            }
        return {
            "privacy_level": "public",
            "confidence": 1.0,
            "sensitive_elements": [],
            "recommendation": "Local-only mode active",
        }

    def choose_execution_location(self, privacy_level: str) -> str:
        # Explicitly local-only per user requirement.
        return "local"

