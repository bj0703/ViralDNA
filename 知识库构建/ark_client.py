import os
import json
import requests
from dotenv import load_dotenv
from typing import Dict, Any

DOTENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(DOTENV_PATH)


class ArkClient:
    def __init__(self):
        self.api_key = os.environ.get("ARK_API_KEY", "")
        self.endpoint_id = os.environ.get("ARK_ENDPOINT_ID", "")
        self.base_url = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3/chat/completions")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        payload = {
            "model": self.endpoint_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 4096
        }
        resp = requests.post(self.base_url, headers=self.headers, json=payload, timeout=120)
        resp.raise_for_status()
        result = resp.json()
        content = result["choices"][0]["message"]["content"].strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        return json.loads(content)
