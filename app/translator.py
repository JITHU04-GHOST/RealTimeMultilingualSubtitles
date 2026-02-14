import torch
from transformers import MBart50TokenizerFast, MBartForConditionalGeneration

print("Loading mBART-50 translation model (Hindi + Malayalam)...")

MODEL_NAME = "facebook/mbart-large-50-many-to-many-mmt"

tokenizer = MBart50TokenizerFast.from_pretrained(MODEL_NAME)
model = MBartForConditionalGeneration.from_pretrained(MODEL_NAME)

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)
model.eval()

print("Translator loaded!")

def translate(text: str, lang="en") -> str:
    text = text.strip()
    if not text or lang == "en":
        return text

    tokenizer.src_lang = "en_XX"
    inputs = tokenizer(text, return_tensors="pt", truncation=True).to(device)

    target = "hi_IN" if lang == "hi" else "ml_IN"

    out = model.generate(
        **inputs,
        forced_bos_token_id=tokenizer.lang_code_to_id[target],
        max_length=256,
        num_beams=5
    )

    return tokenizer.decode(out[0], skip_special_tokens=True)
