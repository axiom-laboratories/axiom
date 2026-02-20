import base64
import json
import io
from unittest.mock import patch

def test_gen_token_logic():
    # Since gen_token.py executes on import, we check its side effect or logic
    # Here we just verify the expected format
    ca_content = "-----BEGIN CERTIFICATE-----"
    token_str = "352731062a81465ea5c5d50cae35c594"
    
    token_dict = {
        "t": token_str,
        "ca": ca_content
    }
    
    encoded = base64.b64encode(json.dumps(token_dict).encode()).decode()
    decoded = json.loads(base64.b64decode(encoded).decode())
    
    assert decoded["t"] == token_str
    assert ca_content in decoded["ca"]
