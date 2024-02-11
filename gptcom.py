import json
from openai import OpenAI
from datetime import datetime, timezone

class OutOfTokensException(Exception):
    pass
# A communicator class to easily send API requests to OpenAI API and store the message log
# Is a separate class in case we end up swapping out GPT-4 for a smaller language model like Llama or Mistral
class GPTCommunicator:

    current_messages = []

    def __init__(self,client,model_name):
        self.client = client
        self.model_name = model_name

    # Main send command that sends everything stored in current_messages to the API and saves the response
    def send(self):
        completion = self.client.chat.completions.create(
            model = self.model_name,
            messages= self.current_messages
        )
        self.saveResponse(completion.choices[0].message.content)
        return completion.choices[0]

    # Sends a "system" role message, declaring the context for this exchange (ex. "You are a financial expert")
    def setBehavior(self,system_behavior):
        self.system_behavior = system_behavior
        self.current_messages.append({"role": "system", "content":system_behavior})

    # Formats and sends a user question
    def askGPT(self,message):
        self.current_messages.append({"role": "user", "content":message})

    # Formats and saves a response
    def saveResponse(self,response):
        self.current_messages.append({"role": "assistant", "content":response})

    # Clears message history
    def flush(self):
        self.current_messages = []
        self.setBehavior(self.system_behavior)

class SummarizationPrompter:

    # Initializes and sets behavior
    def __init__(self, communicator,config):
        self.communicator = communicator
        self.config = config
        self.communicator.setBehavior(config["behavior"])

    # Sends a summarization task to ChatGPT with the prompt outlined in the config
    # Summary will have a length between min_length and max_length and will focus on extracting information about {focus}. If there is no relevant information about {focus}, function should return NO INFO
    def requestSummary(self, article, focus="everything", min_length=50, max_length=200):
        self.communicator.askGPT(self.config["summary_prompt"].format(minimum=min_length,maximum=max_length,focus=focus,a=article))
        return self.communicator.send().message.content

    def summarizeAll(self, summaries, min_length=50, max_length=200):
        joined_summaries = ";".join(summaries)
        self.communicator.askGPT(self.config["summarize_all_prompt"].format(text=joined_summaries,min_words=min_length,max_words=max_length))
        return self.communicator.send().message.content

    def lookForCatalyst(self, text):
        self.communicator.askGPT(self.config["catalyst_prompt"].format(text=text))
        return self.communicator.send().message.content

    def getSentiment(self, summaries):
        joined_summaries = ";".join(summaries)
        self.communicator.askGPT(self.config["sentiment_prompt"].format(text=text))
        return self.communicator.send().message.content

# Disects user questions into data ready for Polygon API
class QuestionAnalysisPrompter:

    def __init__(self, communicator,config):
        self.communicator = communicator
        self.config = config
        self.communicator.setBehavior(config["behavior"])

    def identifyTimeFrame(self, message):
        today = datetime.now(timezone.utc)
        self.communicator.askGPT(self.config["time_frame_prompt"].format(text=message, date_today=today))
        message = self.communicator.send().message.content
        print(message)

        if message == "NONE":
            return None,None

        before, after = message.split(", ")
        return before, after

    def identifyCompany(self, message):
        self.communicator.askGPT(self.config["company_identification_prompt"].format(text=message))
        #TODO Create an array of tickers
        return self.communicator.send().message.content

# --- TEST CODE ---
# file = open("config.json")
# config = json.load(file)["prompts"]["question_analyzer"]
# file.close()

# client = OpenAI()
# question_prompter = QuestionAnalysisPrompter(GPTCommunicator(client, "gpt-4"), config)

# question = "Why is AAPL moving today?"

# print(question_prompter.identifyTimeFrame(question))
# print(question_prompter.identifyCompany(question))
