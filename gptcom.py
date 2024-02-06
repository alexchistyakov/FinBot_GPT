# A communicator class to easily send API requests to OpenAI API and store the message log
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

    # Initializes and sets behavior
    def __init__(self, communicator,config):
        self.communicator = communicator
        self.config = config
        self.communicator.setBehavior(config["behavior"])

    # Sends a summarization task to ChatGPT with the prompt outlined in the config
    def requestSummary(self,article, min_length=50, max_length=200):
        self.communicator.askGPT(self.config["summary_prompt"].format(minimum=min_length,maximum=max_length,a=article))
        return self.communicator.send().message.content

