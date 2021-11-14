from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


sid = SentimentIntensityAnalyzer()


def get_text_sentiment(text) -> float:
    return from_sentiment_intensity_analyzer(text)


def from_textblob(text) -> float:
    return TextBlob(text).sentiment.polarity


def from_sentiment_intensity_analyzer(text) -> float:
    return sid.polarity_scores(str(text)).get('compound', 0)


if __name__ == "__main__":
    s = 'I personally like Connors idea about having to present an anime a month I think that would be fun!!!'
    print('TextBlob:', from_textblob(s))
    print('SentimentIntensityAnalyzer:', from_sentiment_intensity_analyzer(s))
    print('get_text_sentiment(text):', get_text_sentiment(s))
