import json
import timeit
from gptcom import GPTCommunicator,SummarizationPrompter, QuestionAnalysisPrompter
from polygoncom import PolygonAPICommunicator
from openai import OpenAI
from datetime import datetime, timezone, timedelta

class FinBot:

    # Dictionary for storing summaries by ticker so we can preform QA, request sentiment, etc. with them later
    summaries = {}

    def __init__(self, polygon_key, openai_client, config):

        # Create a my custom client to communicate/parse requests from the PolygonAPI
        self.polygon_com = PolygonAPICommunicator(polygon_key)
        # COMING SOON
        # self.question_prompter = QuestionAnalysisPrompter(GPTCommunicator(client, "gpt-4"), config["prompts"]["question_analyzer"]

        # Create a prompter to make requests and log conversation for news summaries and question analysis
        self.summary_prompter = SummarizationPrompter(GPTCommunicator(openai_client, config["model-name"]), config["prompts"]["summarizer"])

    def getNewsSummariesForTicker(self, ticker, date_after, date_before, min_length=10, max_length=90, limit=20):

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

    def getOverallSummary(self, summaries, min_length=10, max_length=30):

        # Get only text
        text_only_summaries = []
        for summary in summaries:
            text_only_summaries.append(summary["text"])

        return self.summary_prompter.summarizeAll(text_only_summaries, min_length=min_length, max_length=max_length)

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

# --- EXAMPLE: Get the news summaries for AAPL for today ---

# Do some date retrival and formatting first
today = datetime.now(timezone.utc)
yesterday = today - timedelta(days=1)

formatting_string = "%Y-%m-%dT%H:%M:%SZ"

today_string = today.strftime(formatting_string)
yesterday_string = yesterday.strftime(formatting_string)

# Get the summaries
summaries = finbot.getNewsSummariesForTicker("AAPL", yesterday_string, today_string, limit=20)

# Print news summaries as a test
print("--------------FINAL SUMMARIES------------------")
for summary in summaries:
    print(summary)
    print("---------------------------------")

print(finbot.getOverallSummary(summaries))

# --- END EXAMPLE ---

# Stop timing and print the elapsed time
end_time = timeit.default_timer() - start_time
print("Time Elapsed: {time} seconds".format(time=end_time))


