import json
import timeit
from ai.prompters import SummarizationPrompter, QuestionAnalysisPrompter
from financial.polygon import *
from openai import OpenAI, RateLimitError, BadRequestError
from datetime import datetime, timezone, timedelta
from ai.communicators import HuggingFaceCommunicator, GPTCommunicator

from CacheToolsUtils import RedisCache
import hashlib
import redis
from cachetools.keys import hashkey

class FinBot:

    key_path = "../keys.json"
    config_path = "config.json"

    def __init__(self):
        # Load configuration and initialize services
        self._load_configuration()
        self._initialize_services()
        self._initialize_cache()

    def _load_configuration(self):
        with open(self.config_path) as config_file, open(self.key_path) as key_file:
            self.config = json.load(config_file)
            self.polygon_key = json.load(key_file)["POLYGON_API"]

    def _initialize_services(self):
        # Setup based on configuration
        if self.config["use-gpt"]:
            openai_client = OpenAI()
            gpt_communicator = GPTCommunicator(openai_client, self.config["model-name"])
            self.question_prompter = QuestionAnalysisPrompter(gpt_communicator, self.config["prompts"]["question_analyzer"])
            self.summary_prompter = SummarizationPrompter(gpt_communicator, self.config["prompts"]["summarizer"])
        else:
            communicator = HuggingFaceCommunicator(self.config["model-name"])
            self.question_prompter = QuestionAnalysisPrompter(communicator, self.config["prompts"]["question_analyzer"])
            self.summary_prompter = SummarizationPrompter(communicator, self.config["prompts"]["summarizer"])

        self.polygon_com = PolygonAPICommunicator(self.polygon_key)

    def _initialize_cache(self):
        if self.config["cache"]["cache-output"]:
            self.cache = RedisCache(redis.Redis(host=self.config["cache"]["redis-host"], port=self.config["cache"]["redis-port"]), ttl=None)
        else:
            self.cache = None

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
        news = self.polygon_com.get_news(ticker, datetime_after, datetime_before, limit)
        name = self.polygon_com.get_name(ticker)

        try:

            summaries = []

            for pair in news:
                summary = None
                # Try retrieving from cache. If not, generate it
                if self.cache != None:
                    cache_key = str([pair["url"],ticker])
                    # Generate the summary
                    try:
                        summary = self.cache.get(cache_key)["extracted_summary"]
                        print("Retrieved from cache")
                    except KeyError:
                        try:
                            summary = self.summary_prompter.requestSummary(pair["text"],name=name, focus=ticker, min_length=min_length, max_length=max_length)
                        except BadRequestError:
                            continue
                        # Flush to avoid token overflow
                        self.summary_prompter.communicator.flush()

                        self.cache.set(cache_key, {
                            "ticker":ticker,
                            "text": pair["text"],
                            "extracted_summary": summary
                            }
                        )
                        print("Saved to cache")

                else:
                    try:
                        summary = self.summary_prompter.requestSummary(pair["text"], focus=ticker,name=name, min_length=min_length, max_length=max_length)
                    except BadRequestError:
                        continue
                    # Flush to avoid token overflow
                    self.summary_prompter.communicator.flush()

                # Check to make sure there was relevant information in this article about ticker since Polygon API sometimes returns irrelevant articles that briefly mention the ticker. If so, add it to the list of summaries
                #if summary != "NO INFO":
                print("=====================[ {source} ]=======================".format(source=pair["source"]))
                print(pair["text"])
                print("\nURL: "+pair["url"])
                print("--------------------SUMMARY-----------------------")
                print(summary)
                print("=====================================================")
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
def temp(ticker):
    today = datetime.now(timezone.utc)
    yesterday = today - timedelta(days=21900)
    finbot.getNewsSummariesForTicker(ticker, yesterday, today,limit=10)

finbot = FinBot()
tickers = finbot.polygon_com.get100Tickers()

temp("NFLX")
temp("TSLA")
temp("MARA")
temp("PLTR")
temp("MSTR")
temp("MU")
temp("RDDT")
temp("BA")
temp("CLSK")
temp("BABA")
temp("NKE")
temp("SOUN")
temp("DIS")
temp("SNOW")
temp("AAPL")
temp("KO")
temp("CAKE")
temp("PG")
temp("PYPL")
