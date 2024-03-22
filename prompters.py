class AIPrompter:

    def __init__(self, communicator, config):
        self.communicator = communicator
        self.config = config


class SummarizationPrompter(AIPrompter):

    # Sends a summarization task to ChatGPT with the prompt outlined in the config
    # Summary will have a length between min_length and max_length and will focus on extracting information about {focus}. If there is no relevant information about {focus}, function should return NO INFO
    def requestSummary(self, article, focus="everything", name=None, min_length=50, max_length=200):
        self.communicator.ask(self.config["summary_prompt"].format(minimum=min_length,maximum=max_length,focus=focus,a=article, name=name))
        result = self.communicator.send()
        self.communicator.flush()
        return result

    def selfVerifySummary(self, summary, ticker):
        self.communicator.ask(self.config["self-verification-prompt"].format(ticker=ticker,text=summary))
        result = self.communicator.send()
        self.communicator.flush()

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
