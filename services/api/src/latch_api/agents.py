import json
import os
import uuid

import boto3
from botocore.config import Config

from latch_core import config

# Set in AWS: every agent action runs on the deployed Bedrock AgentCore runtime.
# Unset locally: the same entrypoint runs in-process.
AGENTCORE_RUNTIME_ARN = os.environ.get("AGENTCORE_RUNTIME_ARN")

_client = (
    boto3.client("bedrock-agentcore", region_name=config.AWS_REGION, config=Config(read_timeout=900, retries={"max_attempts": 1}))
    if AGENTCORE_RUNTIME_ARN
    else None
)


def invoke(payload: dict) -> dict:
    """Run one agent action ('extract' | 'pursue' | 'adjudicate' | 'tick')."""
    if _client is None:
        from latch_agent.main import invoke as local_invoke

        return local_invoke(payload)

    response = _client.invoke_agent_runtime(
        agentRuntimeArn=AGENTCORE_RUNTIME_ARN,
        runtimeSessionId=f"latch-{uuid.uuid4()}",
        payload=json.dumps(payload).encode(),
    )
    return json.loads(response["response"].read())
