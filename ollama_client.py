import os
import requests


# ============================================================
# OLLAMA CONFIGURATION
# ============================================================

OLLAMA_URL = "http://127.0.0.1:11434"

# Optional:
# You can force a specific model by setting:
#
# $env:FINPILOT_MODEL="qwen3:4b"
#
# Otherwise FinPilot automatically finds an installed Qwen model.

FORCED_MODEL = os.environ.get(
    "FINPILOT_MODEL",
    ""
).strip()


# ============================================================
# CHECK OLLAMA
# ============================================================

def check_ollama():
    try:
        response = requests.get(
            f"{OLLAMA_URL}/api/tags",
            timeout=5
        )

        return response.status_code == 200

    except requests.RequestException:
        return False


# ============================================================
# GET INSTALLED MODELS
# ============================================================

def get_models():
    try:
        response = requests.get(
            f"{OLLAMA_URL}/api/tags",
            timeout=5
        )

        response.raise_for_status()

        data = response.json()

        models = []

        for model in data.get("models", []):
            name = model.get("name")

            if name:
                models.append(name)

        return models

    except (
        requests.RequestException,
        ValueError
    ):
        return []


# ============================================================
# FIND QWEN MODEL
# ============================================================

def get_qwen_model():

    models = get_models()

    if not models:
        raise RuntimeError(
            "No Ollama models were found.\n"
            "Make sure Ollama is running and run:\n"
            "ollama list"
        )

    # If user explicitly selected a model
    if FORCED_MODEL:

        if FORCED_MODEL in models:
            return FORCED_MODEL

        raise RuntimeError(
            f"Model '{FORCED_MODEL}' is not installed.\n\n"
            f"Installed models:\n"
            + "\n".join(models)
        )

    # Preferred Qwen models
    preferred_models = [
        "qwen3:4b",
        "qwen3:1.7b",
        "qwen2.5:3b",
        "qwen2.5:1.5b",
        "qwen2.5:7b",
        "qwen3:8b"
    ]

    for model in preferred_models:

        if model in models:
            return model

    # Find any Qwen model
    qwen_models = [
        model
        for model in models
        if "qwen" in model.lower()
    ]

    if qwen_models:
        return qwen_models[0]

    raise RuntimeError(
        "No Qwen model was found in Ollama.\n\n"
        "Installed models:\n"
        + "\n".join(models)
    )


# ============================================================
# ASK OLLAMA / QWEN
# ============================================================

def ask_ollama(
    prompt,
    model=None
):

    if not prompt or not prompt.strip():
        raise ValueError(
            "Prompt cannot be empty."
        )

    # Automatically select Qwen
    if model is None:
        model = get_qwen_model()

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,

        "options": {
            # Lower temperature makes financial answers
            # more accurate and consistent.
            "temperature": 0.25,

            "top_p": 0.9,

            "repeat_penalty": 1.05,

            # Larger context for financial reasoning.
            "num_ctx": 8192
        }
    }

    try:

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=180
        )

        response.raise_for_status()

    except requests.ConnectionError:

        raise RuntimeError(
            "Could not connect to Ollama.\n"
            "Make sure Ollama is running."
        )

    except requests.Timeout:

        raise RuntimeError(
            "Ollama took too long to respond."
        )

    except requests.RequestException as error:

        raise RuntimeError(
            f"Ollama request failed: {error}"
        )

    try:

        data = response.json()

    except ValueError:

        raise RuntimeError(
            "Ollama returned invalid JSON."
        )

    answer = data.get(
        "response",
        ""
    )

    if not answer:

        raise RuntimeError(
            f"Ollama returned an empty response "
            f"from model '{model}'."
        )

    return answer.strip()