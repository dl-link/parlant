from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ServerConfig:
    port: int = int(os.getenv("PARLANT_SERVER_PORT", "8800"))
    provider_profile: str = os.getenv("PARLANT_PROVIDER_PROFILE", "openai")
    local_playground_url: str = os.getenv("PARLANT_PLAYGROUND_URL", "http://localhost:8800")


@dataclass
class ProjectConfig:
    name: str = "parlant-accounting-agent-discovery"
    runtime: str = "python>=3.10"
    env_openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    approval_threshold_default: float = float(os.getenv("APPROVAL_THRESHOLD_DEFAULT", "10000"))
    default_currency: str = os.getenv("DEFAULT_CURRENCY", "NZD")
    parlant_home: Path = Path(os.getenv("PARLANT_HOME", ".parlant"))


server_config = ServerConfig()
project_config = ProjectConfig()
