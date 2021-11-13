import os
import pandas as pd

from time import time
from numpy import random

from nltk.corpus import stopwords
from nltk import download
from nltk import word_tokenize

from gensim.similarities import WmdSimilarity
from gensim.models import Word2Vec


NUM_BEST = 1
COMMENTS_DATA_PATH = r'data/comments'
TRANSCRIPT_DATA_PATH = r'data/transcript'

download('punkt')
download('stopwords')  # Download stopwords list.
stop_words = stopwords.words('english')


def preprocess(doc):
    return [w for w in word_tokenize(str(doc).lower()) if w not in stop_words and w.isalpha()]


def train_similarity_model(video_id, transcript_df):
    transcript_df['timestamp'] = transcript_df['duration'].cumsum()
    transcript_df['ten_sec_group'] = transcript_df['timestamp'].div(10).astype(int)

    # chunk_of_speeches = {}
    # for i in range((transcript_df['ten_sec_group'].max())):
    #     section = transcript_df[transcript_df['ten_sec_group'].isin([i, i + 1])]
    #     speech = section['text'].add(' ').sum()
    #     chunk_of_speeches[i] = speech
    #
    # transcript_group_df = pd.DataFrame.from_dict(chunk_of_speeches, orient='index')
    # transcript_group_df = transcript_group_df.reset_index().rename(columns={'index': 'group', 0: 'text'})

    # Group transcripts by ten second windows
    chunk_of_speeches = [
        {'group': group, 'text': ' '.join(transcript_df[(transcript_df['ten_sec_group'] == group)]['text'].tolist())}
        for group in list(transcript_df['ten_sec_group'].unique())
    ]

    transcript_group_df = pd.DataFrame(chunk_of_speeches)
    transcript_group_df['timestamp'] = transcript_group_df \
        .apply(lambda r: int(transcript_df[transcript_df.ten_sec_group == r.group].start.min()), axis=1)

    print("Collecting Dataset...")
    ids = transcript_df['ten_sec_group'].unique().tolist()
    w2v_corpus = []  # Documents to train word2vec on (all transcript groups).
    wmd_corpus = []  # Documents to run queries against (only one restaurant).
    transcript_group_texts = []  # wmd_corpus, with no pre-processing (so we can see the original documents).
    for row in range(len(transcript_group_df)):
        if transcript_group_df.loc[row, 'group'] not in ids:
            continue

        text = transcript_group_df.loc[row, 'text']
        text = preprocess(text)
        w2v_corpus.append(text)

        if transcript_group_df.loc[row, 'group'] in ids:
            # Add to corpus for similarity queries.
            wmd_corpus.append(text)
            transcript_group_texts.append(transcript_group_df.loc[row, 'text'])
    print('Collecting Dataset done..')

    print("Training model...")
    # Train Word2Vec on all the transcripts.
    model = Word2Vec(w2v_corpus, workers=3, size=100, min_count=1)

    # Initialize WmdSimilarity.
    wmd_similarity_instance = WmdSimilarity(wmd_corpus, model, num_best=NUM_BEST)
    # possible sentences come from only the wmd_corpus.
    # WMD based on the word2vec from w2c corpus.
    # you must first build vocabulary before training the model --> usually due to empty w2v_corpus
    print("Training model done...")

    return transcript_group_df, wmd_similarity_instance, transcript_group_texts


def predict_comment_timestamp(text,
                              transcript_group_df,
                              wmd_similarity_instance,
                              transcript_group_texts) -> int:
    try:
        start = time()
        sims = wmd_similarity_instance[preprocess(text)]  # A query is simply a "look-up" in the similarity class.
        transcript_group_text = transcript_group_texts[sims[0][0]]
        timestamp = transcript_group_df[transcript_group_df.text == transcript_group_text]['timestamp'].tolist()[0]

        print(f'predict_comment_timestamp - total time taken: {time() - start:.2f} seconds')

    except IndexError as err:
        print('predict_comment_timestamp - Error: cannot find similar transcript.', err)
        timestamp = None

    return timestamp


if __name__ == "__main__":
    VIDEO_ID = 'xDjoy5Sd3ME'
    VIDEO_TRANSCRIPT_FILE = os.path.join(TRANSCRIPT_DATA_PATH, VIDEO_ID + '.csv')
    VIDEO_COMMENTS_FILE = os.path.join(COMMENTS_DATA_PATH, VIDEO_ID + '.csv')

    df_transcript = pd.read_csv(VIDEO_TRANSCRIPT_FILE)
    df_transcript_grp, instance, documents = train_similarity_model(VIDEO_ID, df_transcript)

    # print('df_transcript:', df_transcript.shape, '\n', df_transcript.head().to_string())
    # print('\n\ndf_transcript_grp:', df_transcript_grp.shape, '\n', df_transcript_grp.head().to_string(max_colwidth=50), '\n')

    df_comments = pd.read_csv(VIDEO_COMMENTS_FILE)
    comments = df_comments['textOriginal'].tolist()

    length_of_comments = [len(comment) for comment in comments]
    df_comments = pd.DataFrame({'length': length_of_comments, 'comments': comments})

    x = int(random.rand() * len(df_transcript_grp))  # random number generator
    x = 56  # fixed number
    comment_text = comments[x]
    print(f'\ncomment index: {x}, text={comment_text}')
    print('video timestamp:', predict_comment_timestamp(comment_text, df_transcript_grp, instance, documents))
