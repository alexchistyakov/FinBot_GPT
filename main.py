import json
import timeit
from gptcom import GPTCommunicator,SummarizationPrompter, QuestionAnalysisPrompter
from polygoncom import PolygonAPICommunicator
from openai import OpenAI
from datetime import datetime, timezone, timedelta

class FinBot:

    # Dictionary for storing summaries by ticker so we can preform QA, request sentiment, etc. with them later
    summaries = {}
    date_formatting_string = "%Y-%m-%dT%H:%M:%SZ"

    def __init__(self, polygon_key, openai_client, config):

        # Create a my custom client to communicate/parse requests from the PolygonAPI
        self.polygon_com = PolygonAPICommunicator(polygon_key)
        # COMING SOON
        # self.question_prompter = QuestionAnalysisPrompter(GPTCommunicator(client, "gpt-4"), config["prompts"]["question_analyzer"]

        # Create a prompter to make requests and log conversation for news summaries and question analysis
        self.summary_prompter = SummarizationPrompter(GPTCommunicator(openai_client, config["model-name"]), config["prompts"]["summarizer"])

    def formatDate(self, date):

        date_string = date.strftime(self.date_formatting_string)
        return date_string

    def getTopGainers(self, include_otc=False):
        return self.polygon_com.getTopGainers(include_otc)

    def getTopLosers(self, include_otc=False):
        return self.polygon_com.getTopLosers(include_otc)

    def getNewsSummariesForTicker(self, ticker, datetime_after, datetime_before, min_length=10, max_length=90, limit=20):

        date_after = self.formatDate(datetime_after)
        date_before = self.formatDate(datetime_before)

        news = self.polygon_com.getNews(ticker, date_after, date_before, limit)
        summaries = []
        for pair in news:
            article = pair["text"]
            summary = self.summary_prompter.requestSummary(article, focus=ticker, min_length=min_length, max_length=max_length)
            # Flush to avoid token overflow
            self.summary_prompter.communicator.flush()

            # Check to make sure there was relevant information in this article about ticker since Polygon API sometimes returns irrelevant articles that briefly mention the ticker. If so, add it to the list of summaries
            if summary != "NO INFO":
                summaries.append({"time" : pair["time"], "text" : summary})

        return summaries

    # Get a summary of summaries
    def getOverallSummary(self, summaries, min_length=10, max_length=30):

        # Get only text
        text_only_summaries = []
        for summary in summaries:
            text_only_summaries.append(summary["text"])

        return self.summary_prompter.summarizeAll(text_only_summaries, min_length=min_length, max_length=max_length)

    # Identify whether a catalyst for a stock's movement exists
    def catalystExists(self, text):
        response = self.summary_prompter.lookForCatalyst(text)
        if response == "YES":
            return True
        else:
            return False

    # TODO: Format object. Temproarily just print statements because I don't know if we will be doing a stream or just a JSON object
    def getGainerSummaries(self):
        gainers = self.getTopGainers()

        # Get the summaries
        for item in gainers:
            ticker = item["ticker"]
            vi = ((item["data"]["volume"] - item["data"]["volume_yesterday"])/item["data"]["volume_yesterday"]) * 100
            print("==================================")

            print("\n")
            print("$ {ticker} [CHANGE PERCENT: {cp}] [PRICE: {p}] [VOLUME INCREASE: {vi}]".format(ticker=ticker, cp=item["data"]["change_percent"], p=item["data"]["price"], vi=vi))
            summaries = self.getNewsSummariesForTicker(ticker, yesterday, today, min_length=10, max_length=90, limit=20)

            print("\n")

            if len(summaries) == 0:
                print("NO NEWS")
            else:
                for summary in summaries:
                    print("{time}: {text}".format(time=summary["time"].strftime("[%m/%d/%Y at %H:%M]"),text=summary["text"]))

            print("\n")

            overallSummary = self.getOverallSummary(summaries)
            if self.catalystExists(overallSummary):
                print(overallSummary)
            else:
                print("No catalyst for price action was found")

            print("\n")

# Load config, keys and sample files
config_file = open("config.json")
sample_file = open("samples.json")
key_file = open("../keys.json")

# Convert config, keys and sample files into dictionaries
config = json.load(config_file)
samples = json.load(sample_file)
keys = json.load(key_file)

# Close files
config_file.close()
sample_file.close()
key_file.close()

# Start timing operation
start_time = timeit.default_timer()

# Create a client connection to OpenAI API
client = OpenAI()

# Create an instance of FinBot
finbot = FinBot(keys["POLYGON_API"], client, config)

# --------- EXAMPLE: Get the news summaries and overall sentiment for top gainers ---------

# Do some date retrival and formatting first
today = datetime.now(timezone.utc)
yesterday = today - timedelta(days=1)

finbot.getGainerSummaries()

# ---------- END EXAMPLE ---------

# Stop timing and print the elapsed time
end_time = timeit.default_timer() - start_time
print("Time Elapsed: {time} seconds".format(time=end_time))


