import requests
import json
from newspaper import Article
import dateutil.parser

class FakeTickerException(Exception):
    pass
# Class for communicating with the Polygon API and formatting/parsing responses into an appropriate fromat
class PolygonAPICommunicator:
    # Will probably implement later when I expand this class's functionality to getting candlesticks
    # end_point = "/v2/reference/news"
    news_request_url = "https://api.polygon.io/v2/reference/news?ticker={ticker}&published_utc.gte={utc_after}&published_utc.lte={utc_before}&limit={limit}&apiKey={api_key}"
    gainers_request_url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/gainers?include_otc={include_otc}&apiKey={api_key}"
    losers_request_url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/losers?include_otc={include_otc}&apiKey={api_key}"
    ticker_url = "https://api.polygon.io/v3/reference/tickers?ticker={ticker}&apiKey={api_key}"
    ticker_list_url = "https://api.polygon.io/v3/reference/tickers?active=true&market=stocks&exchange=XNAS&sort=last_updated_utc&apiKey={api_key}"

    # String for formatting dates for the Polygon API
    date_formatting_string = "%Y-%m-%dT%H:%M:%SZ"

    # Just saves the API key
    def __init__(self, api_key):
        self.api_key = api_key

    def verifyTicker(self, ticker):
        request_url = self.ticker_verification_url.format(ticker = ticker, api_key = self.api_key)
        response = requests.get(request_url).json()
        return len(response["results"]) != 0

    def formatDate(self, date):
        return date.strftime(self.date_formatting_string)

    # Get top 20 gainers
    # Returns an array of dictionaries {ticker : {"volume" : volume, "change_percent": percent cahnge since yesterday, "volume_yesterday" : volume yesterday, "price" : price}
    def getTopGainers(self, include_otc=False):
        request_url = self.gainers_request_url.format(include_otc=include_otc,api_key=self.api_key)
        response = requests.get(request_url).json()
        tickers = [{ "ticker": item["ticker"], "data" : { "volume" : item["day"]["v"], "change_percent" : item["todaysChangePerc"], "volume_yesterday" : item["prevDay"]["v"], "price" : item["min"]["c"] }} for item in response["tickers"]]

        return tickers

    # Same structure as gainers but for losers
    def getTopLosers(self, include_otc):
        request_url = self.losers_request_url.format(include_otc=include_otc,api_key=self.api_key)
        response = requests.get(request_url).json()
        tickers = []
        for item in response["tickers"]:
            result = { item["ticker"] : { "volume" : item["day"]["v"], "change_percent" : item["todaysChangePerc"], "volume_yesterday" : item["prevDay"]["v"], "price" : item["min"]["c"] }}
            tickers.append(result)

        return tickers

    # Get news for a particular stock ticker between date_after and date_before (formatted in UTC). Limited to "limit" amount of articles
    def getNews(self, ticker, utc_after, utc_before, limit):

        date_after = self.formatDate(utc_after)
        date_before = self.formatDate(utc_before)

        # Submit a request to the polygon API
        request_url = self.news_request_url.format(ticker=ticker,utc_after=date_after,utc_before=date_before,limit=limit, api_key=self.api_key)
        response = requests.get(request_url).json()
        articles = []


        # Loop through results
        for result in response["results"]:
            # Get article URL from response
            url = result["article_url"]
            time_published = dateutil.parser.parse(result["published_utc"])

            # Download and parse the article from URL using the Newspaper3k API
            article = Article(url)
            # Try/Catch to avoid exceptions such as prohibited download bc paywall
            try:
                article.download()
                article.parse()
            except:
                # Skip articles that cannot be accessed because of a paywall
                continue

            articles.append({"time" : time_published, "text" : article.text, "url" : url})

        return articles

    def getName(self, ticker):
        request_url = self.ticker_url.format(ticker=ticker,api_key=self.api_key)
        response = requests.get(request_url).json()

        results = response["results"]

        if len(results) != 0:
            return results[0]["name"]

        return None

    # Temp function
    def get100Tickers(self):
        request_url = self.ticker_list_url.format(api_key=self.api_key)
        response = requests.get(request_url).json()

        results = [result["ticker"] for result in response["results"]]
        return results
