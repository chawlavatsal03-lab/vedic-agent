# llm.py
# Local LLM wrapper using llama-cpp-python

from llama_cpp import Llama
import os

# --- Configuration ---
MODEL_PATH = os.path.join("models", "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf")

# Check if the model file exists
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Model file not found at '{MODEL_PATH}'. "
        "Please download the GGUF file and place it in the 'models' folder."
    )

# Initialize the model
# n_ctx is the context window size. 2048 is a safe default for 8GB RAM.
# n_threads should be set to the number of your CPU cores for best performance.
try:
    llm = Llama(
        model_path=MODEL_PATH,
        n_ctx=2048,
        n_threads=os.cpu_count(),  # Use all available CPU cores
        verbose=False              # Set to True for detailed logs
    )
    print("Local LLM loaded successfully.")
except Exception as e:
    print(f"Error loading the LLM: {e}")
    raise

def generate(prompt: str, max_tokens: int = 900) -> str:
    """
    Generate a response from the local LLM.

    Args:
        prompt: The full prompt string.
        max_tokens: The maximum number of new tokens to generate.

    Returns:
        The model's text response as a string.
    """
    try:
        output = llm(
            prompt,
            max_tokens=max_tokens,
            echo=False,
            temperature=0.3,
            top_p=0.85,
        )
        return output['choices'][0]['text'].strip()
    except Exception as e:
        return f"An error occurred during generation: {e}"

if __name__ == "__main__":
    # Quick self-test
    print("Testing local LLM...")
    reply = generate("Reply with exactly: OK")
    print("Model replied:", reply)
    print("llm.py is working.")