import hashlib

import redis

from cachetools import LRUCache
from cachetools.keys import hashkey
from CacheToolsUtils import cached, RedisCache

import json

from openai import OpenAI
from datetime import datetime, timezone
from logger import NeuroLogger

class OutOfTokensException(Exception):
    pass

# A communicator class to easily send API requests to OpenAI API and store the message log
# Is a separate class in case we end up swapping out GPT-4 for a smaller language model like Llama or Mistral
class GPTCommunicator:

    def __init__(self,client,model_name):
        self.client = client
        self.model_name = model_name

        self.current_messages = []
        self.system_behavior = None

    # Main send sub-command. Returns full message history for caching purposes
    #@cached(cache=LRUCache(maxsize=2048), key= lambda a: hashlib.sha256(repr(a.current_messages).encode()).hexdigest())
    #@cached(cache=RedisCache(redis.Redis(host="localhost"),ttl=None), key=lambda a: hashkey(a.current_messages[1]["content"]))
    def sendRaw(self):
        completion = self.client.chat.completions.create(
            model = self.model_name,
            messages= self.current_messages
        )
        res = completion.choices[0].message.content
        self.saveResponse(res)
        return self.current_messages

    # Main send command that sends everything stored in current_messages to the API and saves the response
    def send(self):
        res = self.sendRaw()[-1]["content"]
        return res


    # Sends a "system" role message, declaring the context for this exchange (ex. "You are a financial expert")
    def setBehavior(self,system_behavior):
        if self.system_behavior != None and len(self.current_messages) != 0:
            self.current_messages.pop(0)
        self.system_behavior = system_behavior
        self.current_messages.insert(0,{"role": "system", "content":system_behavior})

    # Formats and sends a user question
    def ask(self,message):
        self.current_messages.append({"role": "user", "content":message})

    # Formats and saves a response
    def saveResponse(self,response):
        self.current_messages.append({"role": "assistant", "content":response})

    # Clears message history
    def flush(self):
        self.current_messages = []
        self.setBehavior(self.system_behavior)

class AIPrompter:

    def __init__(self, communicator, config):
        self.communicator = communicator
        self.config = config


class SummarizationPrompter(AIPrompter):

    # Sends a summarization task to ChatGPT with the prompt outlined in the config
    # Summary will have a length between min_length and max_length and will focus on extracting information about {focus}. If there is no relevant information about {focus}, function should return NO INFO
    def requestSummary(self, article, focus="everything", name=None, min_length=50, max_length=200):

        if "grammar" in self.config:
            self.communicator.setBehavior(self.config["behavior"].format(grammar=self.config["grammar"]["summary_prompt"], example=self.config["grammar"]["summary_example"]))
        else:
            self.communicator.setBehavior(self.config["behavior"])

        self.communicator.ask(self.config["summary_prompt"].format(minimum=min_length,maximum=max_length,focus=focus,a=article, name=name))
        result = self.communicator.send()
        self.communicator.flush()
        return result

    def summarizeAll(self, summaries, min_length=50, max_length=200):
        joined_summaries = ";".join(summaries)
        self.communicator.ask(self.config["summarize_all_prompt"].format(text=joined_summaries,min_words=min_length,max_words=max_length))
        result = self.communicator.send()
        self.communicator.flush()
        return result

    def lookForCatalyst(self, text):
        self.communicator.ask(self.config["catalyst_prompt"].format(text=text))
        result = self.communicator.send()
        self.communicator.flush()
        return result

    def getSentiment(self, summaries):
        joined_summaries = ";".join(summaries)
        self.communicator.ask(self.config["sentiment_prompt"].format(text=text))
        return self.communicator.send()

# Disects user questions into data ready for Polygon API
class QuestionAnalysisPrompter(AIPrompter):

    def identifyTimeFrame(self, message):

        today = datetime.now(timezone.utc)
        self.communicator.ask(self.config["time_frame_prompt"].format(text=message, date_today=today))
        message = self.communicator.send()
        self.communicator.flush()

        if message == "NONE":
            self.logger.logDateDescription(message, "NONE", "NONE")
            return None,None

        before, after = message.split(", ")


        return before, after

    def identifyCompany(self, message):

        self.communicator.ask(self.config["company_identification_prompt"].format(text=message))

        return self.communicator.send()

# --- TEST CODE ---
# file = open("config.json")
# config = json.load(file)["prompts"]["question_analyzer"]
# file.close()

# client = OpenAI()
# question_prompter = QuestionAnalysisPrompter(GPTCommunicator(client, "gpt-4"), config)

# question = "Why is AAPL moving today?"

# print(question_prompter.identifyTimeFrame(question))
# print(question_prompter.identifyCompany(question))
