CWE_PATTERNS: dict[str, dict[str, object]] = {
    "CWE-79": {
        "name": "Cross-site Scripting",
        "keywords": ["<script", "onerror=", "javascript:"],
        "typical_sinks": ["template rendering", "HTML output"],
    },
    "CWE-89": {
        "name": "SQL Injection",
        "keywords": ["SELECT", "UNION", "OR 1=1"],
        "typical_sinks": ["cursor.execute", "ORM raw query", "string interpolation"],
    },
    "CWE-78": {
        "name": "OS Command Injection",
        "keywords": [";", "&&", "|", "$(", "`"],
        "typical_sinks": ["os.system", "subprocess"],
    },
    "CWE-22": {
        "name": "Path Traversal",
        "keywords": ["../", "..\\"],
        "typical_sinks": ["open", "Path", "file write"],
    },
    "CWE-502": {
        "name": "Deserialization of Untrusted Data",
        "keywords": ["pickle", "yaml.load", "marshal"],
        "typical_sinks": ["pickle.loads", "yaml.load"],
    },
    "CWE-918": {
        "name": "Server-Side Request Forgery",
        "keywords": ["http://", "https://", "169.254.169.254"],
        "typical_sinks": ["requests.get", "urllib"],
    },
    "CWE-798": {
        "name": "Use of Hard-coded Credentials",
        "keywords": ["api_key", "secret", "password"],
        "typical_sinks": ["source code literals", "config defaults"],
    },
    "CWE-327": {
        "name": "Use of a Broken or Risky Cryptographic Algorithm",
        "keywords": ["md5", "sha1", "des", "rc4", "ecb"],
        "typical_sinks": ["hashlib.md5", "Crypto.Cipher"],
    },
}
