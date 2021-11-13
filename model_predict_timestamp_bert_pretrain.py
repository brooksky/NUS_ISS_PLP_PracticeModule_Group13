import torch
import os
import pandas as pd

from transformers import BertTokenizer, BertModel
from scipy.spatial.distance import cosine


COMMENTS_DATA_PATH = r'data/comments'
TRANSCRIPT_DATA_PATH = r'data/transcript'


def bert_segment_task(tokenized_text):
    common_punctuations = ['.', '?', '!']
    new_t = ['[CLS]']
    for position in range(len(tokenized_text)):
        try:
            if tokenized_text[position] in common_punctuations \
                    and tokenized_text[position + 1] not in common_punctuations:
                new_t.append(tokenized_text[position])
                new_t.append('[SEP]')
            else:
                new_t.append(tokenized_text[position])
        except:
            pass

    if new_t[len(new_t) - 1] != '[SEP]':
        new_t.append('[SEP]')

    return new_t


def bert_segment_task_2(new_t):
    sentence_id = 0
    segment_ids = []
    for word in new_t:
        if word == '[SEP]':
            segment_ids.append(sentence_id)
            sentence_id += 1
        else:
            segment_ids.append(sentence_id)

    return segment_ids


def churn_embeddings(indexed_tokens, segments_ids, model):
    try:
        tokens_tensor = torch.tensor([indexed_tokens])
        segments_tensor = torch.tensor([segments_ids])

        with torch.no_grad():
            outputs = model(tokens_tensor, segments_tensor)
            hidden_states = outputs[2]

        token_vecs = hidden_states[-2][0]

        # Calculate the average of all 22 token vectors.
        sentence_embedding = torch.mean(token_vecs, dim=0)
    except:
        return None

    return sentence_embedding


def find_most_similar(x):
    try:
        most_similar_index = \
            df_transcripts_new['embeddings'] \
                .apply(lambda transcript: 1 - cosine(transcript, x)) \
                .sort_values(ascending=False) \
                .head(1) \
                .index.tolist()[0]
        most_similar_index = int(most_similar_index)
    except:
        return None
    return most_similar_index


class TimestampByBertPretrain:

    def __init__(self):
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-uncased', do_lower_case=True)
        self.model = BertModel.from_pretrained('bert-base-uncased', output_hidden_states=True)

        self.video_transcript_embeddings = {}

    def generate_transcript_embeddings(self, video_id, transcript_df) -> None:
        if video_id not in self.video_transcript_embeddings:
            transcript_df['timestamp'] = transcript_df['duration'].cumsum()
            transcript_df['ten_sec_group'] = transcript_df['start'].add(transcript_df['duration']).div(10).astype(int)

            chunk_of_speech = {}
            for n in range((transcript_df['ten_sec_group'].max())):
                section_df = transcript_df[transcript_df['ten_sec_group'].isin([n, n + 1])]
                speech_str = section_df['text'].add(' ').sum()
                chunk_of_speech[i] = speech_str

            transcript_groups_df = pd.DataFrame.from_dict(chunk_of_speech, orient='index')
            transcript_groups_df.columns = ['textOriginal']

            self.video_transcript_embeddings[video_id] = transcript_groups_df

        return self.video_transcript_embeddings[video_id]


if __name__ == '__main__':
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.float_format', lambda x: '%.3f' % x)

    VIDEO_ID = 'ZSowePnsWXI'
    VIDEO_TRANSCRIPT_FILE = os.path.join(TRANSCRIPT_DATA_PATH, VIDEO_ID + '.csv')
    VIDEO_COMMENTS_FILE = os.path.join(COMMENTS_DATA_PATH, VIDEO_ID + '.csv')

    """
    Manage Transcripts
    """
    df_transcript = pd.read_csv(VIDEO_TRANSCRIPT_FILE)
    df_transcript['timestamp'] = df_transcript['duration'].cumsum()
    df_transcript['ten_sec_group'] = df_transcript['start'].add(df_transcript['duration']).div(10).astype(int)
    print('df_transcript:', df_transcript.shape, '\n', df_transcript.head().to_string(), '\n')

    chunk_of_speeches = {}
    for i in range((df_transcript['ten_sec_group'].max())):
        section = df_transcript[df_transcript['ten_sec_group'].isin([i, i + 1])]
        speech = section['text'].add(' ').sum()
        chunk_of_speeches[i] = speech

    transcript_group_df = pd.DataFrame.from_dict(chunk_of_speeches, orient='index')
    transcript_group_df.columns = ['textOriginal']
    transcript_group_df['type'] = 'transcript'
    print('transcript_group_df:', transcript_group_df.shape, '\n', transcript_group_df.head().to_string(), '\n')

    """
    Manage Comments
    """
    df_comments = pd.read_csv(VIDEO_COMMENTS_FILE)
    df_comments['textOriginal'] = df_comments['textOriginal'].apply(lambda x: '[CLS] ' + x + ' [SEP]')
    df_comments = df_comments[['textOriginal']]
    df_comments['type'] = 'comments'
    print('df_comments:', df_comments.shape, '\n', df_comments.head().to_string(), '\n')

    # To execute all preprocessing on all comments
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased', do_lower_case=True)
    df_combined = transcript_group_df.append(df_comments)
    df_combined['tokenized'] = df_combined['textOriginal'].apply(tokenizer.tokenize)
    df_combined['tokenized'] = df_combined['tokenized'].apply(bert_segment_task)
    df_combined['segment_embedding'] = df_combined['tokenized'].apply(bert_segment_task_2)
    df_combined['indexed_tokens'] = df_combined['tokenized'].apply(tokenizer.convert_tokens_to_ids)
    print('df_combined:', df_combined.shape, '\n', df_combined.head().to_string(), '\n')

    """
    Churn word embeddings
    """
    model = BertModel.from_pretrained('bert-base-uncased', output_hidden_states=True)
    df_combined['embeddings'] = df_combined.apply(lambda x: churn_embeddings(x['indexed_tokens'], x['segment_embedding'], model), axis=1)

    """
    Sentence Vectors
    """
    df_comments_new = df_combined[df_combined.type == 'comments']
    df_comments_new['most_similar'] = df_comments_new['embeddings'].apply(find_most_similar)
    print('df_comments_new:', df_comments_new.shape, '\n', df_comments_new.head().to_string(), '\n')

    print('test a comment output:\n', df_comments_new[df_comments_new['textOriginal'].str.contains('putting it in water is cool, I wou')]
          [['textOriginal', 'most_similar']])

    df_transcripts_new = df_combined[df_combined.type == 'transcript']
    print('textOriginal', df_transcripts_new.loc[[42], ['textOriginal']])
    print(df_transcript[df_transcript.text.str.contains('the best in picture quali')])
