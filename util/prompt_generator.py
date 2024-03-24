import torch
import json
from datetime import datetime, timezone
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from langchain.prompts import PromptTemplate
from langchain_community.llms.huggingface_pipeline import HuggingFacePipeline

model = "mistralai/Mistral-7B-Instruct-v0.2"

# If GPU available use it
device = "cuda" if torch.cuda.is_available() else "cpu"
# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(model)
# Load model
model = AutoModelForCausalLM.from_pretrained(
    model,
    attn_implementation="flash_attention_2",
    torch_dtype=torch.float16,
    device_map='auto',
    load_in_8bit = True
    #device_map = {
    #    "transformer.word_embeddings": 0,
    #    "transformer.word_embeddings_layernorm": 0,
    #    "lm_head": "cpu",
    #    "transformer.h": 0,
    #    "transformer.ln_f": 0
    #},
    #quantization_config = BitsAndBytesConfig(
    #    load_in_8bit = True,
    #    load_in_4bit = False,
    #    llm_int8_enable_fb32_cpu_offload = True
    #)
)
# Set to eval mode
model.eval()
# Create a pipline
generate_text = pipeline(task="text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=300,
        repetition_penalty=1.1,
        model_kwargs= {
            "device_map": "auto",
            "max_length": 1200,
            "temperature": 0.01,
            "torch_dtype": torch.bfloat16
    }
)

prompt_file = open("generator_prompt.txt")
prompt = prompt_file.read()
prompt_file.close()


print(generate_text(prompt))
