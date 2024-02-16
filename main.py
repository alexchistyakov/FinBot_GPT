import json
import timeit
from gptcom import GPTCommunicator,SummarizationPrompter, QuestionAnalysisPrompter
from polygoncom import PolygonAPICommunicator, FakeTickerException
from openai import OpenAI, RateLimitError
from datetime import datetime, timezone, timedelta

class FinBot:
    # Dictionary for storing summaries by ticker so we can preform QA, request sentiment, etc. with them later
    date_formatting_string = "%Y-%m-%dT%H:%M:%SZ"

    def __init__(self):

        openai_client = OpenAI()

        # Load config, keys and sample files
        config_file = open("config.json")
        key_file = open("../keys.json")

        # Convert config, keys and sample files into dictionaries
        self.config = json.load(config_file)
        polygon_key = json.load(key_file)["POLYGON_API"]

        # Close files
        config_file.close()
        key_file.close()

        # Create a my custom client to communicate/parse requests from the PolygonAPI
        self.polygon_com = PolygonAPICommunicator(polygon_key)
        self.question_prompter = QuestionAnalysisPrompter(GPTCommunicator(openai_client, "gpt-4"), self.config["prompts"]["question_analyzer"])

        # Create a prompter to make requests and log conversation for news summaries and question analysis
        self.summary_prompter = SummarizationPrompter(GPTCommunicator(openai_client, self.config["model-name"]), self.config["prompts"]["summarizer"])

    def formatDate(self, date):

        return date.strftime(self.date_formatting_string)

    def smartDateParse(self, text):

        after, before = self.question_prompter.identifyTimeFrame(text)
        before = datetime.strptime(before, "%Y-%m-%d %H:%M:%S%z") if before != None else None
        after = datetime.strptime(after, "%Y-%m-%d %H:%M:%S%z") if after != None else None

        return before, after

    def smartNewsSummariesForTicker(self, ticker, date_text, min_length=10, max_length=30, limit=20):
        before, after = self.smartDateParse(date_text)

        # TEMP CODE FOR DEMO
        summaries = self.getNewsSummariesForTicker(ticker, after, before, min_length=min_length, max_length=max_length, limit=limit)

        if "error" in summaries:
            return summaries

        for summary in summaries:
            print("[{time}] : {text}".format(time=summary["time"], text=summary["text"]))

        overall = self.getOverallSummary(summaries)
        print("\n")
        print(overall)

        return {"summaries":summaries, "overall_summary": overall}

        # return self.getNewsSummariesForTicker(ticker, after, before, min_length=min_length, max_length=max_length, limit=limit)

    def getTopGainers(self, include_otc=False):

        return self.polygon_com.getTopGainers(include_otc)

    def getTopLosers(self, include_otc=False):

        return self.polygon_com.getTopLosers(include_otc)

    def getNewsSummariesForTicker(self, ticker, datetime_after, datetime_before, min_length=10, max_length=90, limit=20):

        date_after = self.formatDate(datetime_after)
        date_before = self.formatDate(datetime_before)

        try:
            news = self.polygon_com.getNews(ticker, date_after, date_before, limit)
        except FakeTickerException as e:
            return {"error": "NOT A REAL TICKER"}

        try:

            summaries = []

            for pair in news:
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

        # Get only text
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

    # TODO: Format object. Temproarily just print statements because I don't know if we will be doing a stream or just a JSON object
    def getGainerSummaries(self, amount=20):
        gainers = self.getTopGainers()[:amount-1]

        res = []
        # Get the summaries
        for item in gainers:
            ticker = item["ticker"]
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
