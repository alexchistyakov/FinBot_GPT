import json

# A communicator class to easily send API requests to OpenAI API and store the message log
class GPTCommunicator:

    client = None
    model_name = "gpt-3.5-turbo"

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

class SummarizationPrompter:

    communicator = None

    def __init__(self, communicator):
        self.communicator = communicator
        self.communicator.setBehavior("You are a financial expert")

    # Sends a summarization task to ChatGPT
    def requestSummary(self,article, min_length=50, max_length=200):
        self.communicator.askGPT("In a minimum of {minimum} words and maximum of {maximum} words, summarize the following text, keeping it as short as possible while still encapsulating the main points: {a}".format(minimum=min_length,maximum=max_length,a=article))
        return self.communicator.send().message.content

