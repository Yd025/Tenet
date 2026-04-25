from uagents import Agent, Context
from protocols.chat_protocol import (
    PrivacyAnalysisRequest, PrivacyAnalysisResponse,
    chat_protocol, PrivacyLevel
)
from config.agent_config import AgentConfig
import re

class TenetPrivacyRouter:
    """Privacy analysis and routing agent"""
    
    def __init__(self):
        self.config = AgentConfig()
        
        # Initialize the privacy router agent
        self.agent = Agent(
            name="tenet-privacy-router",
            seed=self.config.PRIVACY_ROUTER_SEED,
            port=self.config.PRIVACY_ROUTER_PORT
        )
        
        # Privacy patterns
        self.privacy_patterns = {
            # Financial patterns
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b': 'credit_card',
            r'\b\d{9,11}\b': 'ssn',
            r'\bbank\s+account\b': 'bank_account',
            r'\brouting\s+number\b': 'routing_number',
            
            # Medical patterns
            r'\bmedical\s+record\b': 'medical_record',
            r'\bhealth\s+information\b': 'health_info',
            r'\bdiagnosis\b': 'medical_diagnosis',
            r'\bprescription\b': 'medical_prescription',
            
            # Security patterns
            r'\bpassword\b': 'password',
            r'\bprivate\s+key\b': 'private_key',
            r'\bapi\s+key\b': 'api_key',
            r'\bsecret\b': 'secret',
            r'\btoken\b': 'security_token',
            
            # Personal patterns
            r'\bconfidential\b': 'confidential',
            r'\bpersonal\s+information\b': 'personal_info',
            r'\bssn\b': 'ssn',
            r'\bsocial\s+security\b': 'ssn'
        }
        
        # Setup protocol handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup privacy analysis handlers"""
        
        @chat_protocol.on_message(model=PrivacyAnalysisRequest)
        async def handle_privacy_analysis(ctx: Context, sender: str, msg: PrivacyAnalysisRequest):
            """Analyze content for privacy concerns"""
            
            try:
                # Perform privacy analysis
                analysis_result = self.analyze_content_privacy(msg.content)
                
                # Create response
                response = PrivacyAnalysisResponse(
                    privacy_level=analysis_result["level"],
                    confidence=analysis_result["confidence"],
                    sensitive_elements=analysis_result["sensitive_elements"],
                    recommendation=analysis_result["recommendation"]
                )
                
                await ctx.send(sender, response)
                
            except Exception as e:
                # Error handling - default to private for safety
                error_response = PrivacyAnalysisResponse(
                    privacy_level=PrivacyLevel.PRIVATE,
                    confidence=0.5,
                    sensitive_elements=[],
                    recommendation=f"Error in analysis: {str(e)}. Defaulting to private routing."
                )
                await ctx.send(sender, error_response)
    
    def analyze_content_privacy(self, content: str) -> dict:
        """Analyze content for privacy concerns"""
        
        content_lower = content.lower()
        sensitive_elements = []
        confidence_score = 0.0
        
        # Check for privacy patterns
        for pattern, element_type in self.privacy_patterns.items():
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            if matches:
                sensitive_elements.extend([element_type] * len(matches))
                confidence_score += 0.2
        
        # Check for sensitive keywords
        for keyword in self.config.SENSITIVE_KEYWORDS:
            if keyword in content_lower:
                if keyword not in sensitive_elements:
                    sensitive_elements.append(keyword)
                confidence_score += 0.1
        
        # Determine privacy level based on findings
        if confidence_score >= 0.7:
            privacy_level = PrivacyLevel.SENSITIVE
            recommendation = "Route to local model for maximum privacy"
        elif confidence_score >= 0.3:
            privacy_level = PrivacyLevel.PRIVATE
            recommendation = "Route to private cloud instance or local model"
        else:
            privacy_level = PrivacyLevel.PUBLIC
            recommendation = "Route to standard cloud API"
        
        # Cap confidence at 1.0
        confidence_score = min(confidence_score, 1.0)
        
        return {
            "level": privacy_level,
            "confidence": confidence_score,
            "sensitive_elements": list(set(sensitive_elements)),  # Remove duplicates
            "recommendation": recommendation
        }
    
    def run(self):
        """Start the privacy router agent"""
        self.agent.include(chat_protocol)
        print("🔒 Tenet Privacy Router Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print(f"🔗 Privacy Analysis: Enabled")
        print(f"🛡️  Protected Patterns: {len(self.privacy_patterns)}")
        self.agent.run()

# Run the privacy router
if __name__ == "__main__":
    privacy_router = TenetPrivacyRouter()
    privacy_router.run()
