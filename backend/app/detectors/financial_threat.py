import re
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from urllib.parse import urlparse
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ThreatEntity:
    type: str
    value: str
    position: int
    confidence: float
    metadata: Dict[str, Any]


@dataclass
class ThreatTactic:
    name: str
    description: str
    confidence: float
    evidence: List[str]


class FinancialThreatDetector:
    """
    Financial scam detection with entity extraction, threat intelligence
    cross-referencing, and psychological tactic classification.
    """

    # Regex patterns for entity extraction
    PATTERNS = {
        "phone": [
            r'(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}',
            r'(?:\+?\d{1,3}[-.\s]?)?\d{10,12}',
        ],
        "email": [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        ],
        "url": [
            r'https?://[^\s<>"\']+',
            r'www\.[^\s<>"\']+',
        ],
        "crypto_btc": [
            r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b',  # Legacy BTC
            r'\bbc1[a-zA-HJ-NP-Z0-9]{39,59}\b',      # Bech32 BTC
        ],
        "crypto_eth": [
            r'\b0x[a-fA-F0-9]{40}\b',  # Ethereum/ERC20
        ],
        "crypto_generic": [
            r'\b[A-Za-z0-9]{32,64}\b',  # Generic long alphanumeric
        ],
        "iban": [
            r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b',
        ],
        "swift_bic": [
            r'\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b',
        ],
        "credit_card": [
            r'\b(?:\d{4}[-.\s]?){3}\d{4}\b',
        ],
        "amount": [
            r'(?:\$|USD|EUR|GBP|₹|¥)\s*\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?',
            r'\b\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP|dollars?|euros?|pounds?|rupees?)\b',
        ],
        "account_number": [
            r'\b\d{8,17}\b',  # Generic account numbers
        ],
        "routing_number": [
            r'\b\d{9}\b',  # US routing
        ],
    }

    # Psychological tactics with keyword indicators
    TACTICS = {
        "urgency": {
            "keywords": [
                "immediately", "urgent", "asap", "right now", "hurry", "quickly",
                "deadline", "expires", "limited time", "act now", "don't delay",
                "last chance", "final notice", "time sensitive", "within 24 hours",
                "today only", "before it's too late"
            ],
            "description": "Creates false time pressure to bypass critical thinking",
            "weight": 1.0,
        },
        "authority_impersonation": {
            "keywords": [
                "bank manager", "security department", "fraud team", "compliance",
                "government", "irs", "tax authority", "police", "fbi", "official",
                "representative", "officer", "agent", "verification team",
                "customer service", "support team", "technical support",
                "microsoft", "apple", "amazon", "google", "paypal", "bank of america",
                "wells fargo", "chase", "citi", "capital one"
            ],
            "description": "Pretends to be from legitimate authority or trusted organization",
            "weight": 1.2,
        },
        "fear_intimidation": {
            "keywords": [
                "suspended", "closed", "frozen", "blocked", "compromised", "hacked",
                "unauthorized", "suspicious activity", "investigation", "legal action",
                "lawsuit", "arrest", "criminal", "fraud alert", "security breach",
                "identity theft", "stolen", "lost access", "permanently closed"
            ],
            "description": "Threatens negative consequences to induce panic",
            "weight": 1.1,
        },
        "greed_reward": {
            "keywords": [
                "won", "winner", "prize", "lottery", "inheritance", "refund",
                "reimbursement", "compensation", "bonus", "reward", "gift",
                "free money", "cash back", "stimulus", "grant", "beneficiary",
                "unclaimed", "fortune", "million", "billion"
            ],
            "description": "Promises financial gain to override skepticism",
            "weight": 1.0,
        },
        "scarcity": {
            "keywords": [
                "limited", "exclusive", "only", "few left", "running out",
                "last few", "almost gone", "unique opportunity", "one time",
                "special offer", "invitation only", "selected", "chosen"
            ],
            "description": "Creates false scarcity to pressure quick decisions",
            "weight": 0.8,
        },
        "social_proof": {
            "keywords": [
                "others have", "everyone is", "thousands of", "customers agree",
                "recommended by", "trusted by", "testimonial", "review",
                "rating", "verified", "proven", "guaranteed"
            ],
            "description": "Uses fake social validation to build trust",
            "weight": 0.7,
        },
        "reciprocity": {
            "keywords": [
                "free", "complimentary", "no obligation", "risk free",
                "try before", "sample", "gift for you", "our gift",
                "as a token", "appreciation"
            ],
            "description": "Offers something free to create obligation",
            "weight": 0.6,
        },
        "credential_harvesting": {
            "keywords": [
                "verify your", "confirm your", "update your", "validate your",
                "login", "password", "pin", "ssn", "social security",
                "date of birth", "mother's maiden", "account number",
                "card number", "cvv", "expiry", "credentials"
            ],
            "description": "Requests sensitive personal/financial information",
            "weight": 1.3,
        },
        "remote_access": {
            "keywords": [
                "teamviewer", "anydesk", "remote access", "screen sharing",
                "install", "download", "app", "software", "tool",
                "grant access", "control your", "help you fix"
            ],
            "description": "Requests remote access to device for 'support'",
            "weight": 1.2,
        },
        "payment_demand": {
            "keywords": [
                "wire transfer", "western union", "moneygram", "bitcoin",
                "cryptocurrency", "gift card", "itunes card", "google play card",
                "steam card", "prepaid card", "money order", "cash deposit",
                "zelle", "venmo", "cashapp", "paypal friends"
            ],
            "description": "Demands payment via irreversible/traceable methods",
            "weight": 1.4,
        },
    }

    # Known suspicious patterns
    SUSPICIOUS_PATTERNS = {
        "generic_greeting": [
            r"dear (customer|user|client|sir|madam|friend)",
            r"hello (customer|user|there)",
        ],
        "poor_grammar": [
            r"\b(i am|i'm) (writing|contacting) (you|to you) (because|as|since)",
            r"kindly (request|ask|provide|send|verify)",
            r"please (find|see|check|verify|confirm) (attached|below|the)",
        ],
        "suspicious_tld": [
            r"\.(tk|ml|ga|cf|xyz|top|club|work|date|faith|loan|accountant|download|racing|win|bid|review|party|science|stream|trade|webcam|men|gq)\b",
        ],
        "url_shortener": [
            r"(bit\.ly|tinyurl|t\.co|goo\.gl|ow\.ly|is\.gd|buff\.ly|adf\.ly|bc\.vc|shorte\.st)\/",
        ],
        "ip_address_url": [
            r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
        ],
    }

    def __init__(self):
        self.compiled_patterns = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile all regex patterns."""
        for category, patterns in self.PATTERNS.items():
            self.compiled_patterns[category] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        for category, patterns in self.SUSPICIOUS_PATTERNS.items():
            self.compiled_patterns[f"suspicious_{category}"] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    async def detect(
        self,
        text: str,
        language: Optional[str] = None,
        extract_entities: bool = True,
        check_threat_intel: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze text for financial scam indicators.
        """
        try:
            # Detect language if not provided
            if language is None:
                language = self._detect_language(text)
            
            # Extract entities
            entities = []
            if extract_entities:
                entities = self._extract_entities(text)
            
            # Detect psychological tactics
            tactics = self._detect_tactics(text)
            
            # Check suspicious patterns
            suspicious_flags = self._check_suspicious_patterns(text)
            
            # Cross-reference with threat intel (placeholder for API integration)
            threat_intel = {}
            if check_threat_intel:
                threat_intel = await self._check_threat_intelligence(entities)
            
            # Compute overall risk score
            risk_score = self._compute_risk_score(entities, tactics, suspicious_flags, threat_intel)
            
            # Determine threat level
            is_threat = risk_score > settings.FINANCIAL_THREAT_THRESHOLD
            confidence = risk_score if is_threat else (1.0 - risk_score)
            
            # Generate explanations
            explanations = self._generate_explanations(
                is_threat, risk_score, entities, tactics, suspicious_flags, threat_intel
            )

            return {
                "detector": "financial_threat",
                "is_threat": is_threat,
                "confidence": round(confidence, 4),
                "risk_score": round(risk_score, 4),
                "threat_level": self._risk_to_level(risk_score),
                "entities": entities,
                "tactics": [t.__dict__ for t in tactics],
                "suspicious_patterns": suspicious_flags,
                "threat_intelligence": threat_intel,
                "language": language,
                "explanations": explanations,
            }

        except Exception as e:
            logger.error(f"Financial threat detection failed: {e}")
            return {
                "detector": "financial_threat",
                "is_threat": False,
                "confidence": 0.0,
                "risk_score": 0.0,
                "threat_level": "error",
                "entities": [],
                "tactics": [],
                "suspicious_patterns": [],
                "threat_intelligence": {},
                "explanations": [{
                    "type": "processing_error",
                    "message": f"Analysis failed: {str(e)}",
                    "severity": "error"
                }],
            }

    def _detect_language(self, text: str) -> str:
        """Simple language detection."""
        try:
            from langdetect import detect
            return detect(text)
        except:
            return "en"

    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract financial entities from text."""
        entities = []
        
        for category, patterns in self.compiled_patterns.items():
            if category.startswith("suspicious_"):
                continue
                
            for pattern in patterns:
                for match in pattern.finditer(text):
                    entity = {
                        "type": category,
                        "value": match.group(),
                        "position": match.start(),
                        "confidence": self._entity_confidence(category, match.group()),
                        "metadata": self._entity_metadata(category, match.group()),
                    }
                    entities.append(entity)
        
        # Deduplicate overlapping entities
        entities = self._deduplicate_entities(entities)
        
        # Sort by position
        entities.sort(key=lambda e: e["position"])
        
        return entities

    def _entity_confidence(self, category: str, value: str) -> float:
        """Assign confidence based on entity type and format validity."""
        if category in ["crypto_btc", "crypto_eth"]:
            return 0.95  # Very specific formats
        elif category in ["iban", "swift_bic", "routing_number"]:
            return 0.9
        elif category in ["phone", "email", "url"]:
            return 0.85
        elif category == "credit_card":
            return 0.8 if self._luhn_check(value) else 0.3
        elif category == "amount":
            return 0.7
        else:
            return 0.6

    def _entity_metadata(self, category: str, value: str) -> Dict[str, Any]:
        """Add metadata for specific entity types."""
        metadata = {}
        
        if category == "url":
            parsed = urlparse(value if value.startswith("http") else "http://" + value)
            metadata["domain"] = parsed.netloc
            metadata["path"] = parsed.path
            metadata["is_shortener"] = any(
                s in parsed.netloc for s in ["bit.ly", "tinyurl", "t.co", "goo.gl"]
            )
            metadata["is_ip"] = bool(re.match(r'\d+\.\d+\.\d+\.\d+', parsed.netloc))
            metadata["tld"] = parsed.netloc.split('.')[-1] if '.' in parsed.netloc else ""
            
        elif category in ["crypto_btc", "crypto_eth"]:
            metadata["currency"] = "BTC" if category == "crypto_btc" else "ETH"
            
        elif category == "phone":
            # Extract country code
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 10:
                metadata["country_code"] = digits[:-10] if len(digits) > 10 else "1"
                metadata["national_number"] = digits[-10:]
        
        return metadata

    def _luhn_check(self, card_number: str) -> bool:
        """Validate credit card with Luhn algorithm."""
        digits = [int(d) for d in re.sub(r'\D', '', card_number)]
        if len(digits) < 13:
            return False
        checksum = 0
        for i, d in enumerate(reversed(digits)):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d
        return checksum % 10 == 0

    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """Remove overlapping entities, keeping highest confidence."""
        if not entities:
            return []
            
        entities.sort(key=lambda e: (e["position"], -e["confidence"]))
        result = [entities[0]]
        
        for entity in entities[1:]:
            last = result[-1]
            if entity["position"] < last["position"] + len(last["value"]):
                # Overlapping - keep higher confidence
                if entity["confidence"] > last["confidence"]:
                    result[-1] = entity
            else:
                result.append(entity)
                
        return result

    def _detect_tactics(self, text: str) -> List[ThreatTactic]:
        """Detect psychological manipulation tactics."""
        text_lower = text.lower()
        detected_tactics = []
        
        for tactic_name, tactic_info in self.TACTICS.items():
            matches = []
            for keyword in tactic_info["keywords"]:
                if keyword.lower() in text_lower:
                    matches.append(keyword)
            
            if matches:
                # Confidence based on number of matches and weight
                confidence = min(
                    len(matches) * 0.15 * tactic_info["weight"], 1.0
                )
                detected_tactics.append(ThreatTactic(
                    name=tactic_name,
                    description=tactic_info["description"],
                    confidence=confidence,
                    evidence=matches[:5],  # Limit evidence
                ))
        
        # Sort by confidence
        detected_tactics.sort(key=lambda t: t.confidence, reverse=True)
        return detected_tactics

    def _check_suspicious_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Check for suspicious patterns."""
        flags = []
        text_lower = text.lower()
        
        for category, patterns in self.compiled_patterns.items():
            if not category.startswith("suspicious_"):
                continue
                
            for pattern in patterns:
                matches = list(pattern.finditer(text))
                if matches:
                    flags.append({
                        "type": category.replace("suspicious_", ""),
                        "count": len(matches),
                        "examples": [m.group()[:50] for m in matches[:3]],
                        "severity": self._pattern_severity(category),
                    })
        
        return flags

    def _pattern_severity(self, category: str) -> str:
        severity_map = {
            "suspicious_suspicious_tld": "high",
            "suspicious_url_shortener": "medium",
            "suspicious_ip_address_url": "high",
            "suspicious_generic_greeting": "low",
            "suspicious_poor_grammar": "low",
        }
        return severity_map.get(category, "medium")

    async def _check_threat_intelligence(
        self, entities: List[Dict]
    ) -> Dict[str, Any]:
        """Cross-reference entities with threat intelligence feeds."""
        # This is a placeholder for real API integrations
        # In production, integrate with:
        # - VirusTotal API
        # - AbuseIPDB
        # - PhishTank
        # - Custom threat feeds
        # - Blockchain analytics (Chainalysis, CipherTrace)
        
        results = {
            "checked_entities": 0,
            "malicious_entities": [],
            "suspicious_entities": [],
            "clean_entities": [],
        }
        
        for entity in entities:
            if entity["type"] in ["url", "domain", "ip", "crypto_btc", "crypto_eth", "email"]:
                results["checked_entities"] += 1
                
                # Simulate threat intel check
                # In reality, make async HTTP calls to threat intel APIs
                is_malicious = await self._mock_threat_check(entity)
                
                if is_malicious:
                    results["malicious_entities"].append({
                        "entity": entity,
                        "source": "threat_intel",
                        "categories": ["phishing", "malware", "scam"],
                    })
                elif self._heuristic_suspicious(entity):
                    results["suspicious_entities"].append({
                        "entity": entity,
                        "reason": "heuristic_flags",
                    })
                else:
                    results["clean_entities"].append(entity)
        
        return results

    async def _mock_threat_check(self, entity: Dict) -> bool:
        """Mock threat intelligence check - replace with real API calls."""
        # Simulate some known bad patterns
        value = entity["value"].lower()
        
        # Known bad TLDs
        if entity["type"] == "url":
            metadata = entity.get("metadata", {})
            if metadata.get("is_ip") or metadata.get("is_shortener"):
                return True
            if metadata.get("tld") in ["tk", "ml", "ga", "cf", "xyz", "top"]:
                return True
                
        # Known scam crypto addresses (example)
        if entity["type"] in ["crypto_btc", "crypto_eth"]:
            # In reality, check against blockchain analytics APIs
            pass
            
        return False

    def _heuristic_suspicious(self, entity: Dict) -> bool:
        """Heuristic checks for suspicious entities."""
        if entity["type"] == "url":
            metadata = entity.get("metadata", {})
            if metadata.get("is_shortener") or metadata.get("is_ip"):
                return True
        return False

    def _compute_risk_score(
        self,
        entities: List[Dict],
        tactics: List[ThreatTactic],
        suspicious_flags: List[Dict],
        threat_intel: Dict,
    ) -> float:
        """Compute overall risk score (0-1)."""
        score = 0.0
        
        # Entity-based risk
        entity_weights = {
            "crypto_btc": 0.15, "crypto_eth": 0.15, "crypto_generic": 0.1,
            "phone": 0.05, "email": 0.05, "url": 0.1,
            "iban": 0.1, "swift_bic": 0.1, "credit_card": 0.15,
            "amount": 0.05, "account_number": 0.05, "routing_number": 0.05,
        }
        
        for entity in entities:
            weight = entity_weights.get(entity["type"], 0.03)
            score += weight * entity["confidence"]
        
        # Tactic-based risk
        for tactic in tactics:
            score += tactic.confidence * 0.12
        
        # Suspicious pattern risk
        for flag in suspicious_flags:
            severity_weight = {"high": 0.15, "medium": 0.08, "low": 0.03}
            score += severity_weight.get(flag["severity"], 0.05) * flag["count"]
        
        # Threat intel risk
        malicious_count = len(threat_intel.get("malicious_entities", []))
        suspicious_count = len(threat_intel.get("suspicious_entities", []))
        score += malicious_count * 0.3 + suspicious_count * 0.1
        
        # Cap at 1.0
        return min(score, 1.0)

    def _risk_to_level(self, risk_score: float) -> str:
        if risk_score >= 0.8:
            return "critical"
        elif risk_score >= 0.6:
            return "high"
        elif risk_score >= 0.4:
            return "medium"
        elif risk_score >= 0.2:
            return "low"
        return "minimal"

    def _generate_explanations(
        self,
        is_threat: bool,
        risk_score: float,
        entities: List[Dict],
        tactics: List[ThreatTactic],
        suspicious_flags: List[Dict],
        threat_intel: Dict,
    ) -> List[Dict[str, Any]]:
        explanations = []
        
        # Overall assessment
        level = self._risk_to_level(risk_score)
        explanations.append({
            "type": "overall_assessment",
            "message": f"Financial threat level: {level.upper()} (risk score: {risk_score:.2f})",
            "severity": "error" if level in ["critical", "high"] else "warning" if level == "medium" else "info",
            "details": {
                "risk_score": round(risk_score, 3),
                "threat_level": level,
                "is_threat": is_threat,
            }
        })
        
        # Entities found
        if entities:
            entity_summary = {}
            for e in entities:
                entity_summary[e["type"]] = entity_summary.get(e["type"], 0) + 1
            
            explanations.append({
                "type": "entities_detected",
                "message": f"Detected {len(entities)} financial entities: {', '.join(f'{v} {k}' for k, v in entity_summary.items())}",
                "severity": "info",
                "details": {"entities": entities[:10]},  # Limit for response size
            })
            
            # Highlight high-risk entities
            high_risk = [e for e in entities if e["type"] in ["crypto_btc", "crypto_eth", "credit_card", "iban"]]
            if high_risk:
                explanations.append({
                    "type": "high_risk_entities",
                    "message": f"High-risk entities detected: {', '.join(e['type'] for e in high_risk)}",
                    "severity": "warning",
                    "details": {"entities": high_risk},
                })
        
        # Tactics detected
        if tactics:
            top_tactics = tactics[:3]
            explanations.append({
                "type": "psychological_tactics",
                "message": f"Detected {len(tactics)} manipulation tactic(s): {', '.join(t.name.replace('_', ' ').title() for t in top_tactics)}",
                "severity": "warning",
                "details": {
                    "tactics": [
                        {
                            "name": t.name,
                            "description": t.description,
                            "confidence": round(t.confidence, 2),
                            "evidence": t.evidence[:3],
                        }
                        for t in top_tactics
                    ]
                }
            })
        
        # Suspicious patterns
        if suspicious_flags:
            for flag in suspicious_flags:
                explanations.append({
                    "type": "suspicious_pattern",
                    "message": f"Suspicious pattern: {flag['type'].replace('_', ' ')} ({flag['count']} occurrences)",
                    "severity": flag["severity"],
                    "details": flag,
                })
        
        # Threat intelligence
        malicious = threat_intel.get("malicious_entities", [])
        if malicious:
            explanations.append({
                "type": "threat_intel_match",
                "message": f"⚠️ {len(malicious)} entity(ies) matched known threat intelligence",
                "severity": "error",
                "details": {"matches": malicious[:5]},
            })
        
        suspicious = threat_intel.get("suspicious_entities", [])
        if suspicious:
            explanations.append({
                "type": "threat_intel_suspicious",
                "message": f"{len(suspicious)} entity(ies) flagged by heuristic analysis",
                "severity": "warning",
                "details": {"entities": suspicious[:5]},
            })
        
        # Recommendations
        if is_threat:
            explanations.append({
                "type": "recommendation",
                "message": "Do not provide personal information, click links, or send money. Verify independently through official channels.",
                "severity": "info",
                "details": {
                    "actions": [
                        "Contact the organization directly using official contact info",
                        "Do not use phone numbers/links from the suspicious message",
                        "Report to relevant authorities (FTC, IC3, local police)",
                        "Enable 2FA on all financial accounts",
                    ]
                }
            })
        
        return explanations