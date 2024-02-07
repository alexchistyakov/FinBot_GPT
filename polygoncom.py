import requests
import json
from newspaper import Article

# Class for communicating with the Polygon API and formatting/parsing responses into an appropriate fromat
class PolygonAPICommunicator:
    # Will probably implement later when I expand this class's functionality to getting candlesticks
    # end_point = "/v2/reference/news"
    news_request_url = "https://api.polygon.io/v2/reference/news?ticker={ticker}&published_utc.gte={utc_after}&published_utc.lte={utc_before}&limit={limit}&apiKey={api_key}"

    # Just saves the API key
    def __init__(self, api_key):
        self.api_key = api_key

    # Get news for a particular stock ticker between date_after and date_before (formatted in UTC). Limited to "limit" amount of articles
    def getNews(self, ticker, date_after, date_before, limit):

        # Submit a request to the polygon API
        # TODO Add error handling for bad requests
        request_url = self.news_request_url.format(ticker=ticker,utc_after=date_after,utc_before=date_before,limit=limit, api_key=self.api_key)
        response = requests.get(request_url).json()
        articles = []

        # Loop through results
        for result in response["results"]:
            # Get article URL from response
            url = result["article_url"]

            # Download and parse the article from URL using the Newspaper3k API
            article = Article(url)
            # Try/Catch to avoid exceptions such as prohibited download bc paywall
            try:
                article.download()
                article.parse()
            except:
                continue

            articles.append(article.text)

        return articles

# --- TEST CODE ---
# keys_file = open("../keys.json")
# key = json.load(keys_file)["POLYGON_API"]
# keys_file.close()

# communicator = PolygonAPICommunicator(key)
# news = communicator.getNews("AAPL", "2023-02-01T00:00:00Z", "2023-05-01T00:00:00Z", 10)
# for text in news:
#     print("------------------------------------------------------------------")
#     print(text)
# print(len(news))
