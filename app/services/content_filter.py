"""
JODOHKU.MY — Content Filter Service
Lexical regex scanning for URLs, phone numbers, and prohibited content
"""

import re
from typing import Dict


class ContentFilterService:
    """
    Scans chat messages for prohibited content.
    Triggers strike system on violation.
    """

    # URL patterns
    URL_PATTERNS = [
        r'https?://\S+',
        r'www\.\S+',
        r'bit\.ly/\S+',
        r'tinyurl\.com/\S+',
        r'goo\.gl/\S+',
        r't\.co/\S+',
    ]

    # Phone number request patterns (Malay + English)
    PHONE_PATTERNS = [
        r'\b01\d[\s\-]?\d{3,4}[\s\-]?\d{4}\b',    # Malaysian phone format
        r'\b\+?60\d{9,10}\b',                        # +60 format
        r'\bwhatsapp\b',
        r'\bwasap\b',
        r'\bwassap\b',
        r'\bwhatsap\b',
        r'\bwa\s?me\b',
        r'\btelegram\b',
        r'\bwechat\b',
        r'\bsignal\b',
        r'\bfon\b',
        r'\btepon\b',
        r'\btelefon\b',
        r'\bphone\b',
        r'\bnombor\b.*\b(fon|hp|telefon)\b',
        r'\bnum(ber)?\b.*\b(phone|hp|call)\b',
        r'\bhubungi\s+(saya|aku)\b',
        r'\bcall\s+me\b',
        r'\bcontact\s+(me|number)\b',
        r'\bberi\s+(no|nombor)\b',
    ]

    # Obscene / inappropriate content
    OBSCENE_PATTERNS = [
        # Malay profanity and sexual references (common patterns)
        r'\bbabi\b',
        r'\bsial\b',
        r'\bbodoh\b',
        r'\bbangsat\b',
        r'\blancau\b',
        r'\bcelaka\b',
        r'\bsundal\b',
        r'\bharam\s?jadah\b',
        # English profanity (basic list)
        r'\bf+u+c+k+\b',
        r'\bs+h+i+t+\b',
        r'\ba+s+s+h+o+l+e+\b',
        r'\bbitch\b',
        r'\bdick\b',
        r'\bpussy\b',
    ]

    # Financial scam patterns
    SCAM_PATTERNS = [
        r'\btransfer\s+(duit|wang|money)\b',
        r'\bpinjam(kan)?\s+(duit|wang|money)\b',
        r'\bbank\s+acc(ount)?\b',
        r'\baccount\s+number\b',
        r'\bnombor\s+akaun\b',
        r'\bpayment\b.*\b(outside|luar)\b',
        r'\binvest(ment|asi)?\b.*\b(peluang|opportunity|return)\b',
        r'\bcrypto\b',
        r'\bbitcoin\b',
        r'\bforex\b',
    ]

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile all regex patterns for performance."""
        self.compiled_url = [re.compile(p, re.IGNORECASE) for p in self.URL_PATTERNS]
        self.compiled_phone = [re.compile(p, re.IGNORECASE) for p in self.PHONE_PATTERNS]
        self.compiled_obscene = [re.compile(p, re.IGNORECASE) for p in self.OBSCENE_PATTERNS]
        self.compiled_scam = [re.compile(p, re.IGNORECASE) for p in self.SCAM_PATTERNS]

    def scan_message(self, content: str) -> Dict:
        """
        Scan message content for violations.
        Returns: { is_clean, reason, reason_ms, reason_en, category }
        """
        # Check URLs
        for pattern in self.compiled_url:
            if pattern.search(content):
                return {
                    "is_clean": False,
                    "reason": "url_detected",
                    "reason_ms": "Pautan tidak dibenarkan di platform ini.",
                    "reason_en": "Links are not allowed on this platform.",
                    "category": "url",
                }

        # Check phone numbers
        for pattern in self.compiled_phone:
            if pattern.search(content):
                return {
                    "is_clean": False,
                    "reason": "phone_request",
                    "reason_ms": "Perkongsian nombor telefon tidak dibenarkan. Gunakan fungsi Mohon WhatsApp.",
                    "reason_en": "Phone number sharing is not allowed. Use the WhatsApp Request feature.",
                    "category": "phone",
                }

        # Check obscene content
        for pattern in self.compiled_obscene:
            if pattern.search(content):
                return {
                    "is_clean": False,
                    "reason": "obscene_content",
                    "reason_ms": "Kandungan lucah atau kesat tidak dibenarkan.",
                    "reason_en": "Obscene or abusive content is not allowed.",
                    "category": "obscene",
                }

        # Check scam patterns
        for pattern in self.compiled_scam:
            if pattern.search(content):
                return {
                    "is_clean": False,
                    "reason": "financial_scam",
                    "reason_ms": "Permintaan kewangan tidak dibenarkan di platform ini.",
                    "reason_en": "Financial requests are not allowed on this platform.",
                    "category": "scam",
                }

        return {
            "is_clean": True,
            "reason": None,
            "reason_ms": None,
            "reason_en": None,
            "category": None,
        }
