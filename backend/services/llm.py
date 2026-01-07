import os
import random
from langchain_openai import ChatOpenAI

def get_llm(model_name="llama-3.3-70b"):
    # Collect all available keys dynamically (CEREBRAS_API_KEY_1, _2, _3...)
    keys = []
    
    # Check legacy single key
    legacy_key = os.getenv("CEREBRAS_API_KEY")
    if legacy_key: keys.append(legacy_key.strip())
    
    # Check numbered keys
    i = 1
    while True:
        k = os.getenv(f"CEREBRAS_API_KEY_{i}")
        if not k:
            break
        keys.append(k.strip())
        i += 1
        
    if keys:
        api_key = random.choice(keys)
        # print(f"DEBUG: Selected Key #{keys.index(api_key)+1} (...{api_key[-4:]})")
    else:
        api_key = None

    if not api_key:
        raise ValueError("No CEREBRAS_API_KEY_x found in .env")
    
    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base="https://api.cerebras.ai/v1",
        temperature=0
    )
