import torch
import json
from datetime import datetime, timezone
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from langchain.prompts import PromptTemplate
from langchain_community.llms.huggingface_pipeline import HuggingFacePipeline

class HuggingFaceCommunicator:

    def __init__(self):
        self.template = """Behavior: {behavior}. Prompt: {query}. Response: """
        #Set model
        model = "tiiuae/falcon-7b-instruct"
        # If GPU available use it
        device = "cuda" if torch.cuda.is_available() else "cpu"
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model)
        # Load model
        model = AutoModelForCausalLM.from_pretrained(
            model,
            load_in_8bit=True,
            device_map='auto'
        )
        # Set to eval mode
        model.eval()
        # Create a pipline
        self.generate_text = pipeline(task="text-generation", model=model, tokenizer=tokenizer,
                                 max_new_tokens=100,
                                 repetition_penalty=1.1, model_kwargs={"device_map": "auto",
                                  "max_length": 1200, "temperature": 0.01, "torch_dtype":torch.bfloat16}
        )

        self.messages = []
        self.prompt_template = PromptTemplate(
                input_variables=["query","behavior"],
                template = self.template
        )

    def ask(self, query):
        self.query = query

    def setBehavior(self, behavior):
        self.behavior = behavior

    def send(self):
        text = self.generate_text(self.prompt_template.format(behavior = self.behavior, query = self.query))[0]["generated_text"]
        response = text.split("Response:",1)[1]
        return response

#----------- TEST CODE ----------------
file = open("config.json")
config = json.load(file)["prompts"]["question_analyzer"]
file.close()

hfcom = HuggingFaceCommunicator()
hfcom.setBehavior(config["behavior"])
# hfcom.ask(config["time_frame_prompt"].format(date_today=datetime.now(timezone.utc), text = "yesterday"))
print(hfcom.send())
