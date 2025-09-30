import pandas as pd
import io, base64
from textblob import TextBlob
from wordcloud import WordCloud
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer

def generate_wordcloud_base64(text, max_words=150):
    if not text:
        text = "sin datos"
    wc = WordCloud(width=800, height=400, background_color='white', max_words=max_words).generate(text)
    buf = io.BytesIO()
    wc.to_image().save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def sentiment_polarity_series(reviews_df, text_col='text'):
    reviews_df = reviews_df.copy()
    reviews_df['polarity'] = reviews_df[text_col].astype(str).apply(lambda t: TextBlob(t).sentiment.polarity)
    return reviews_df

def aggregate_time_series(reviews_df, date_col='date'):
    df = reviews_df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    ts = df.groupby(df[date_col].dt.to_period('M')).size()
    return ts.sort_index().to_dict()

def basic_topic_modeling(texts, n_topics=4, max_features=1000):
    if not texts:
        return []
    vec = CountVectorizer(max_features=max_features, stop_words='english')
    X = vec.fit_transform(texts)
    lda = LatentDirichletAllocation(n_components=n_topics, random_state=0)
    lda.fit(X)
    features = vec.get_feature_names_out()
    topics = []
    for topic_idx, comp in enumerate(lda.components_):
        terms = [features[i] for i in comp.argsort()[-8:][::-1]]
        topics.append({'topic': topic_idx, 'words': terms})
    return topics

def analyze_reviews_from_df(reviews_df, text_col='text', date_col='date', n_topics=4):
    all_text = " ".join(reviews_df[text_col].astype(str).tolist())
    wc_b64 = generate_wordcloud_base64(all_text)
    reviews_df2 = sentiment_polarity_series(reviews_df, text_col=text_col)
    avg_sent = reviews_df2['polarity'].mean() if not reviews_df2.empty else 0.0
    ts = aggregate_time_series(reviews_df2, date_col=date_col)
    topics = basic_topic_modeling(reviews_df[text_col].astype(str).tolist(), n_topics=n_topics)
    return {
        'wordcloud_b64': wc_b64,
        'avg_sentiment': float(avg_sent),
        'time_series': ts,
        'topics': topics
    }
