from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Choose the model: TinyLlama's 1.1B chat version
model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

print(f"Loading tokenizer for {model_id}...")
tokenizer = AutoTokenizer.from_pretrained(model_id)

print(f"Loading model for {model_id}...")
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto"  # Automatically uses GPU if available
)

def ask_tinyllama(prompt, max_new_tokens=50, temperature=0.7, top_p=0.9):
    """
    Generates a response from TinyLlama for a given prompt.
    """

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        do_sample=True
    )

    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print("=== Response ===")
    print(response)
