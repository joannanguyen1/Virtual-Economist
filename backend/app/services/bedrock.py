"""AWS Bedrock client wrapper.

Provides thin helpers for:
  - plain-text model invocations
  - tool-use conversations
  - Titan embeddings
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config
from loguru import logger

# ---------------------------------------------------------------------------
# Model IDs
# ---------------------------------------------------------------------------
NOVA_PRO: str = "amazon.nova-pro-v1:0"  # Nova Pro — powerful reasoning/SQL
NOVA_LITE: str = "amazon.nova-lite-v1:0"  # Nova Lite — fast entity extraction

# Aliases so agent files require no changes
CLAUDE_SONNET: str = NOVA_PRO
CLAUDE_HAIKU: str = NOVA_LITE

# Question-routing classifier — reuse Nova Lite so routing does not depend on
# the retired Titan Text Lite model.
TITAN_TEXT_LITE: str = NOVA_LITE

# Titan Embeddings V1 — 1536 dimensions, matches vector(1536) in DB schema
TITAN_EMBED: str = "amazon.titan-embed-text-v1"

_REGION: str = os.getenv("AWS_REGION", "us-east-1")


@lru_cache(maxsize=1)
def _bedrock_client():
    """Return a cached Bedrock runtime client (one per process).

    Credentials come from the EC2 IAM instance role automatically.
    """
    return boto3.client(
        "bedrock-runtime",
        region_name=_REGION,
        config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
    )


def invoke_claude(
    prompt: str,
    *,
    system: str = "",
    model_id: str = NOVA_PRO,
    max_tokens: int = 2048,
    temperature: float = 0.0,
) -> str:
    """Invoke a Bedrock model via the Converse API and return the text response.

    Uses the unified Converse API, compatible with Nova, Claude, Llama, and
    other Bedrock-hosted models without model-specific request formatting.

    Args:
        prompt:      The user-turn message to send.
        system:      Optional system prompt to set model behavior.
        model_id:    Bedrock model ID (default: Nova Pro).
        max_tokens:  Maximum tokens in the response.
        temperature: Sampling temperature (0 = deterministic).

    Returns:
        The assistant's reply as a plain string.

    Raises:
        Exception: Propagates Bedrock/botocore exceptions to the caller.
    """
    client = _bedrock_client()

    kwargs: dict = {
        "modelId": model_id,
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {
            "maxTokens": max_tokens,
            "temperature": temperature,
        },
    }
    if system:
        kwargs["system"] = [{"text": system}]

    logger.debug(
        "Bedrock invoke | model={} | system_len={} | prompt_len={}",
        model_id,
        len(system),
        len(prompt),
    )

    response = client.converse(**kwargs)
    text: str = response["output"]["message"]["content"][0]["text"].strip()

    logger.debug("Bedrock response | model={} | response_len={}", model_id, len(text))
    return text


def converse_with_tools(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    system: str = "",
    model_id: str = NOVA_PRO,
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> dict[str, Any]:
    """Invoke the Bedrock Converse API with tool definitions enabled."""
    client = _bedrock_client()

    kwargs: dict[str, Any] = {
        "modelId": model_id,
        "messages": messages,
        "toolConfig": {"tools": tools},
        "inferenceConfig": {
            "maxTokens": max_tokens,
            "temperature": temperature,
        },
    }
    if system:
        kwargs["system"] = [{"text": system}]

    logger.debug(
        "Bedrock tool invoke | model={} | messages={} | tools={}",
        model_id,
        len(messages),
        len(tools),
    )
    response = client.converse(**kwargs)
    logger.debug(
        "Bedrock tool response | model={} | stop_reason={}",
        model_id,
        response.get("stopReason"),
    )
    return response


def embed_text(text: str) -> list[float]:
    """Generate a 1536-dimension embedding for *text* using Amazon Titan.

    Uses the Titan Embeddings V1 model which produces vectors of 1536 floats,
    matching the ``vector(1536)`` columns in the database schema.

    Args:
        text: The input string to embed (max ~8k tokens for Titan V1).

    Returns:
        A list of 1536 floats representing the embedding.
    """
    client = _bedrock_client()

    body = json.dumps({"inputText": text})

    logger.debug("Bedrock embed | model={} | text_len={}", TITAN_EMBED, len(text))

    response = client.invoke_model(
        modelId=TITAN_EMBED,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    result: dict = json.loads(response["body"].read())
    embedding: list[float] = result["embedding"]

    logger.debug("Bedrock embed | dims={}", len(embedding))
    return embedding
