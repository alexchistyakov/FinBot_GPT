import hashlib

import torch
import json
from datetime import datetime, timezone
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from langchain.prompts import PromptTemplate
from langchain_community.llms.huggingface_pipeline import HuggingFacePipeline

import redis

import json

# Basic model communicator the implements a message storage mechanism to provide context
class ModelCommunicator:

    def __init__(self):
        self.messages = []
        self.system_behavior = None

    # Store a message
    def ask(self, message):
        self.messages.append({"role":"user", "content":message})

    # Store a system behavior that is resistant to flushing
    def setBehavior(self,system_behavior):
        if self.system_behavior != None and len(self.messages) != 0:
            self.messages.pop(0)
        self.system_behavior = system_behavior
        self.messages.insert(0,{"role": "system", "content":system_behavior})

    # Flush the current messages
    def flush(self):
        self.messages = []
        if self.system_behavior != None:
            self.setBehavior(self.system_behavior)

    # Save response into message history
    def saveResponse(self,response):
        self.messages.append({"role": "assistant", "content":response})

# A communicator class to communicate with a Hugging-Face model
class HuggingFaceCommunicator(ModelCommunicator):

    def __init__(self,model):

        super().__init__()

        # If GPU available use it
        device = "cuda" if torch.cuda.is_available() else "cpu"
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model)
        # Load model
        self.model = AutoModelForCausalLM.from_pretrained(
            model,
            attn_implementation="flash_attention_2",
            torch_dtype=torch.float16,
            device_map='auto',
            #device_map = {
            #    "transformer.word_embeddings": 0,
            #    "transformer.word_embeddings_layernorm": 0,
            #    "lm_head": 0,
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
        self.model.eval()
        # Create a pipline
        self.generate_text = pipeline(task="text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_new_tokens=300,
                repetition_penalty=1.1,
                model_kwargs= {
                    "device_map": "auto",
                    "max_length": 1200,
                    "temperature": 0.01,
                    "torch_dtype": torch.bfloat16
            }
        )

    def send(self):
        text = self.generate_text(self.tokenizer.apply_chat_template(self.messages, tokenize=False))[0]["generated_text"]
        response = text.split("[/INST]",1)[1]
        self.saveResponse(response)
        return response

# A communicator class to easily send API requests to OpenAI API
class GPTCommunicator(ModelCommunicator):

    def __init__(self,client,model_name):
        super().__init__()
        self.client = client
        self.model_name = model_name

    # Main send sub-command.
    def send(self):
        completion = self.client.chat.completions.create(
            model = self.model_name,
            messages= self.messages
        )
        res = completion.choices[0].message.content
        self.saveResponse(res)
        return self.messages[-1]["content"]

# --- TEST CODE ---
# file = open("config.json")
# config = json.load(file)["prompts"]["question_analyzer"]
# file.close()

# client = OpenAI()
# question_prompter = QuestionAnalysisPrompter(GPTCommunicator(client, "gpt-4"), config)

# question = "Why is AAPL moving today?"

# print(question_prompter.identifyTimeFrame(question))
# print(question_prompter.identifyCompany(question))
