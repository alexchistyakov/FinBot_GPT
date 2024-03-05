import json
import timeit
from gptcom import GPTCommunicator,SummarizationPrompter, QuestionAnalysisPrompter
from polygoncom import PolygonAPICommunicator, FakeTickerException
from openai import OpenAI, RateLimitError
from datetime import datetime, timezone, timedelta
from langchainsum import HuggingFaceCommunicator

from CacheToolsUtils import RedisCache
import redis
from cachetools.keys import hashkey

class FinBot:

    def __init__(self):

        # Load config, keys and sample files
        config_file = open("config.json")
        key_file = open("../keys.json")

        # Convert config, keys and sample files into dictionaries
        self.config = json.load(config_file)
        polygon_key = json.load(key_file)["POLYGON_API"]

        communicator = None
        prompts = self.config["prompts"]

        # Check to see whether we are using custom prompts. If so, fetch them
        if self.config["use-custom-prompts"]:
            prompt_file = open("prompts/{file}.json".format(file=self.config["custom-prompt-file"]))
            prompts = json.load(prompt_file)["prompts"]

        # Enable/disable caching
        if self.config["cache"]["cache-output"]:
            self.cache = RedisCache(redis.Redis(host=self.config["cache"]["redis-host"], port=self.config["cache"]["redis-port"]),ttl=None)

        # Determine whether we are using the OpenAI pipeline or a custom HuggingFace model
        if self.config["use-gpt"]:
            # Create the OpenAI client
            openai_client = OpenAI()
            self.question_prompter = QuestionAnalysisPrompter(GPTCommunicator(openai_client,self.config["model-name"]), prompts["question_analyzer"])
            self.summary_prompter = SummarizationPrompter(GPTCommunicator(openai_client,self.config["model-name"]), prompts["summarizer"])

        else:
            # Create a Hugging Face pipeline
            self.question_prompter = QuestionAnalysisPrompter(HuggingFaceCommunicator(self.config["model-name"],prompts["template"]), prompts["question_analyzer"])
            self.summary_prompter = SummarizationPrompter(HuggingFaceCommunicator(self.config["model-name"],prompts["template"]), prompts["summarizer"])

        # Close files
        config_file.close()
        key_file.close()


        # Create a my custom client to communicate/parse requests from the PolygonAPI
        self.polygon_com = PolygonAPICommunicator(polygon_key)

    # Parse date from human input
    def smartDateParse(self, text):

        after, before = self.question_prompter.identifyTimeFrame(text)
        before = datetime.strptime(before, "%Y-%m-%d %H:%M:%S%z") if before != None else None
        after = datetime.strptime(after, "%Y-%m-%d %H:%M:%S%z") if after != None else None

        return before, after

    # Get news summaries for ticker based on parsed dates from human input
    def smartNewsSummariesForTicker(self, ticker, date_text, min_length=10, max_length=30, limit=20):
        before, after = self.smartDateParse(date_text)

        summaries = self.getNewsSummariesForTicker(ticker, after, before, min_length=min_length, max_length=max_length, limit=limit)

        if "error" in summaries:
            return summaries

        for summary in summaries:
            print("[{time}] : {text}".format(time=summary["time"], text=summary["text"]))

        overall = self.getOverallSummary(summaries)
        print("\n")
        print(overall)

        return {"summaries":summaries, "overall_summary": overall}

    # Get news summaries for ticker between date_before and date_after
    def getNewsSummariesForTicker(self, ticker, datetime_after, datetime_before, min_length=10, max_length=90, limit=20):
        news = self.polygon_com.getNews(ticker, datetime_after, datetime_before, limit)

        try:

            summaries = []

            for pair in news:
                summary = None
                # Try retrieving from cache. If not, generate it
                if self.cache != None:
                    try:
                        summary = self.cache.get(pair["url"])["extracted_summary"]
                    except KeyError:
                        # Generate the summary
                        summary = self.summary_prompter.requestSummary(pair["text"], focus=ticker, min_length=min_length, max_length=max_length)
                        # Flush to avoid token overflow
                        self.summary_prompter.communicator.flush()

                        self.cache.set(pair["url"], {
                            "ticker":ticker,
                            "text": pair["text"],
                            "extracted_summary": summary
                            }
                        )

                else:
                    summary = self.summary_prompter.requestSummary(pair["text"], focus=ticker, min_length=min_length, max_length=max_length)
                    # Flush to avoid token overflow
                    self.summary_prompter.communicator.flush()

                # Check to make sure there was relevant information in this article about ticker since Polygon API sometimes returns irrelevant articles that briefly mention the ticker. If so, add it to the list of summaries
                if summary != "NO INFO":
                    summaries.append({"time" : pair["time"], "text" : summary})

            return summaries

        except RateLimitError as e:
            return {"error": "NO MONEY"}

    # Get a summary of summaries
    def getOverallSummary(self, summaries, min_length=10, max_length=50):

        try:
            text_only_summaries = [summary["text"] for summary in summaries]
            return self.summary_prompter.summarizeAll(text_only_summaries, min_length=min_length, max_length=max_length)

        except RateLimitError as e:
            return {"error": "NO MONEY"}

    def getSentiment(self, summaries):

        text_only_summaries = [summary["text"] for summary in summaries]

        return self.summary_prompter.summarizeAll(text_only_summaries)

    # Identify whether a catalyst for a stock's movement exists
    def catalystExists(self, text):

        return True if self.summary_prompter.lookForCatalyst(text) == "YES" else False

    # Get summaries for all top gaining stocks in hopes of identifying a catalyst
    def getGainerSummaries(self, amount=20):
        gainers = self.polygon_com.getTopGainers()[:amount-1]

        res = []
        # Get the summaries
        for item in gainers:
            ticker = item["ticker"]
            # Calculate % volume increase since yesterday and round it down
            vi = round(((item["data"]["volume"] - item["data"]["volume_yesterday"])/item["data"]["volume_yesterday"]) * 100, 2)
            print("==================================")

            print("\n")
            print("$ {ticker} [CHANGE PERCENT: {cp}%] [PRICE: {p}] [VOLUME CHANGE: {vi}%]".format(ticker=ticker, cp=round(item["data"]["change_percent"],2), p=item["data"]["price"], vi=vi))
            resElement = { "ticker" : ticker, "change_percent" : round(item["data"]["change_percent"], 2), "price" : item["data"]["price"], "volume_change": vi }
            today = datetime.now(timezone.utc)
            yesterday = today - timedelta(days=1)

            summaries = self.getNewsSummariesForTicker(ticker, yesterday, today, min_length=10, max_length=90, limit=20)
            resElement["summaries"] = summaries

            print("\n")

            if len(summaries) == 0:
                print("NO NEWS")
                print("\n")
                print("No catalyst for price action was found")
                resElement["overall_summary"] = "No catalyst for price action was found"

            else:

                for summary in summaries:
                    print("{time}: {text}".format(time=summary["time"].strftime("[%m/%d/%Y at %H:%M]"),text=summary["text"]))

                print("\n")

                overallSummary = self.getOverallSummary(summaries)
                if self.catalystExists(overallSummary):
                    print(overallSummary)
                    resElement["overall_summary"] = overallSummary
                else:
                    print("No catalyst for price action was found")
                    resElement["overall_summary"] = "No catalyst for price action was found"

            res.append(resElement)
            print("\n")

        return res

# ----------- TEST CODE -------------
today = datetime.now(timezone.utc)
yesterday = today - timedelta(days=1)

finbot = FinBot()
for summary in finbot.getNewsSummariesForTicker("AAPL", yesterday, today,limit=4):
    print("---------------------------------")
    print(summary["text"])

for summary in finbot.getNewsSummariesForTicker("AAPL", yesterday, today,limit=4):
    print("---------------------------------")
    print(summary["text"])
#finbot.getGainerSummaries()
