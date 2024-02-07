import json
import timeit
from gptcom import GPTCommunicator,SummarizationPrompter, QuestionAnalysisPrompter
from polygoncom import PolygonAPICommunicator
from openai import OpenAI
from datetime import datetime, timezone, timedelta

class FinBot:

    def __init__(self, polygon_key, openai_client, config):

        # Create a my custom client to communicate/parse requests from the PolygonAPI
        self.polygon_com = PolygonAPICommunicator(polygon_key)
        # COMING SOON
        # self.question_prompter = QuestionAnalysisPrompter(GPTCommunicator(client, "gpt-4"), config["prompts"]["question_analyzer"]

        # Create a prompter to make requests and log conversation for news summaries and question analysis
        self.summary_prompter = SummarizationPrompter(GPTCommunicator(openai_client, config["model-name"]), config["prompts"]["summarizer"])

    def getNewsSummariesForTicker(self, ticker, date_after, date_before, limit):

        news = self.polygon_com.getNews(ticker, date_after, date_before, limit)
        summaries = []
        for article in news:
            summaries.append(self.summary_prompter.requestSummary(article, min_length = 10, max_length = 90))

        return summaries

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

print(today_string)

# Get the summaries
summaries = finbot.getNewsSummariesForTicker("AAPL", yesterday_string, today_string, 4)

# Print news summaries as a test
for summary in summaries:
    print(summary)

# Stop timing and print the elapsed time
end_time = timeit.default_timer() - start_time
print("Time Elapsed: {time} seconds".format(time=end_time))

