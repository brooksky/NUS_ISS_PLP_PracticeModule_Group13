import json
import random
import os
import os.path
import re
import datetime

import pandas as pd
import dask.dataframe as dd

from models import model_sentiment
from models import model_predict_video_segment

from flask import Flask, request
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)
API_KEY = os.getenv('YOUTUBE_API_KEY')
COMMENTS_DATA_PATH = r'data/comments'
TRANSCRIPT_DATA_PATH = r'data/transcript'
CHART_NUM_DATA_POINTS = 100
YOUTUBE_API_COMMENT_MAX_RESULTS = 100
IS_DUMMY_DATA = False


# This class is to cache data in memory to prevent calling API multiple times
class DataRetriever:

    def __init__(self):
        # Caching to reduce the need to access storage
        self.video_comments_dict = {}
        self.video_transcript_dict = {}

        self.video_predict_timestamp_model = {}

    def get_comments(self, video_id, video_duration) -> pd.DataFrame:
        if not self.__has_comments_in_storage(video_id):
            self.__store_comments_from_api(video_id)
        return self.__get_comments_from_storage(video_id, video_duration)

    def get_transcript(self, video_id) -> pd.DataFrame:
        if not self.__has_transcript_in_storage(video_id):
            self.__store_transcript_from_api(video_id)
        return self.__get_transcript_from_storage(video_id)

    def get_video_predict_timestamp_model(self, video_id, transcript_df):
        if video_id not in self.video_predict_timestamp_model:
            self.video_predict_timestamp_model[video_id] = \
                model_predict_video_segment.train_similarity_model(video_id, transcript_df.copy())
        return self.video_predict_timestamp_model[video_id]

    def __has_comments_in_storage(self, video_id: str) -> bool:
        return True if video_id in self.video_comments_dict else \
            os.path.isfile(os.path.join(COMMENTS_DATA_PATH, video_id + '.csv'))

    def __has_transcript_in_storage(self, video_id: str) -> bool:
        return True if video_id in self.video_transcript_dict else \
            os.path.isfile(os.path.join(TRANSCRIPT_DATA_PATH, video_id + '.csv'))

    def __get_comments_from_storage(self, video_id, video_duration) -> pd.DataFrame:
        assert self.__has_comments_in_storage(video_id), \
            f'get_comments_from_storage: comments for video_id [{video_id}] is not in storage!'

        if video_id in self.video_comments_dict:
            comments_df = self.video_comments_dict[video_id]
        else:
            comments_df = pd.read_csv(os.path.join(COMMENTS_DATA_PATH, video_id + '.csv'))
            print(f'get_comments_from_storage: video_id={video_id}, shape={comments_df.shape}')

            comments_df['sentiment'] = comments_df.textOriginal.apply(lambda text: predict_comment_sentiment(text))
            comments_df['sentiment_cat'] = comments_df.sentiment \
                .apply(lambda x: 'bad' if x < -0.25 else 'good' if x > 0.25 else 'meh')

            # Start: Comments timestamp section
            if IS_DUMMY_DATA:
                comments_df['time'] = comments_df.apply(lambda x: random.randrange(video_duration), axis=1)
            else:
                start = datetime.datetime.now()

                transcript_df = self.get_transcript(video_id)
                df_transcript_grp, instance, documents = \
                    self.get_video_predict_timestamp_model(video_id, transcript_df)

                # Parallelize pandas apply() using Dask library to speed up processing time
                comments_dd = dd.from_pandas(comments_df, npartitions=60)
                comments_df['time'] = comments_dd \
                    .map_partitions(lambda df: df.apply(lambda row: model_predict_video_segment.predict_comment_timestamp(row['textOriginal'], df_transcript_grp, instance, documents), axis=1)) \
                    .compute(scheduler='processes')

                end = datetime.datetime.now()
                print(f'__get_comments_from_storage - predict timestamp: {(end-start).seconds} seconds')
            # End: Comments timestamp section

            print(comments_df.head())
            self.video_comments_dict[video_id] = comments_df

        return comments_df

    def __get_transcript_from_storage(self, video_id) -> pd.DataFrame:
        assert self.__has_transcript_in_storage(video_id), \
            f'has_transcript_in_storage: transcript for video_id [{video_id}] is not in storage!'

        if video_id in self.video_transcript_dict:
            transcript_df = self.video_transcript_dict[video_id]
        else:
            transcript_df = pd.read_csv(os.path.join(TRANSCRIPT_DATA_PATH, video_id + '.csv'))
            self.video_transcript_dict[video_id] = transcript_df

        return transcript_df

    def __store_transcript_from_api(self, video_id) -> None:
        assert not self.__has_transcript_in_storage(video_id), \
            f'has_transcript_in_storage: transcript for video_id [{video_id}] is already in storage!'

        srt = YouTubeTranscriptApi.get_transcript(video_id)
        df = pd.DataFrame(srt)
        df['text'] = df.text.apply(lambda x: x.replace("\n", " "))

        print('get_and_store_transcript_by_video_id: shape =', df.shape)
        print(df.head())

        df.to_csv(os.path.join(TRANSCRIPT_DATA_PATH, video_id + '.csv'), index=False)

    def __store_comments_from_api(self, video_id) -> None:
        assert not self.__has_comments_in_storage(video_id), \
            f'get_comments_from_storage: comments for video_id [{video_id}] is already in storage!'

        youtube = build('youtube', 'v3', developerKey=API_KEY)

        next_page_token = 'init'
        responses = []
        counter = 0
        while next_page_token is not None and counter <= 5:
            print('counter', counter)
            if next_page_token == 'init':
                response = youtube.commentThreads().list(
                    part="snippet,replies",
                    videoId=video_id,
                    maxResults=YOUTUBE_API_COMMENT_MAX_RESULTS
                ).execute()
            else:
                response = youtube.commentThreads().list(
                    part="snippet,replies",
                    videoId=video_id,
                    maxResults=YOUTUBE_API_COMMENT_MAX_RESULTS,
                    pageToken=next_page_token
                ).execute()

            next_page_token = response.get('nextPageToken', None)
            responses.append(response)
            counter += 1

        comments = [{
            'commentID': comment['id'],
            'authorDisplayName': comment['snippet']['topLevelComment']['snippet']['authorDisplayName'],
            'totalReplyCount': comment['snippet']['totalReplyCount'],
            'textDisplay': comment['snippet']['topLevelComment']['snippet']['textDisplay'],
            'textOriginal': comment['snippet']['topLevelComment']['snippet']['textOriginal'],
            'commentTimestamp':
                self.extract_timestamp_from_comment(comment['snippet']['topLevelComment']['snippet']['textDisplay'])
        } for response in responses for comment in response['items']]

        pd.DataFrame(comments).to_csv(os.path.join(COMMENTS_DATA_PATH, video_id + '.csv'), index=False)
        with open(os.path.join(COMMENTS_DATA_PATH, video_id + '.json'), 'w') as f:
            f.write(json.dumps(responses, indent=4))

    @staticmethod
    def timestamp_str_to_seconds(timestamp_str) -> int:
        timestamp_seconds = 0

        timestamp_str_list = timestamp_str.split('t=')
        timestamp_str = timestamp_str_list[1]

        if 'h' in timestamp_str:
            # extract hours
            timestamp_str_list = timestamp_str.split('h')
            timestamp_str = timestamp_str_list[1]
            timestamp_seconds += int(timestamp_str_list[0]) * 60 * 60

        # extract minutes
        timestamp_str_list = timestamp_str.split('m')
        timestamp_str = timestamp_str_list[1]
        timestamp_seconds += int(timestamp_str_list[0]) * 60

        # extract seconds
        timestamp_str_list = timestamp_str.split('s')
        timestamp_seconds += int(timestamp_str_list[0])

        return timestamp_seconds

    @staticmethod
    def extract_timestamp_from_comment(comment_text):
        # match string: t=0m57s, t=2m35s, t=43m25s, t=2h12m22s
        reg_str = r't=(\d+h)?(\d{1,2}m)(\d{2}s)'
        timestamp_match = re.search(reg_str, comment_text)
        return DataRetriever.timestamp_str_to_seconds(timestamp_match.group()) if timestamp_match else None


dataRetriever = DataRetriever()


@app.route("/api/video")
def init_video():
    # To populate the cache
    video_id = request.args.get('videoId')
    video_duration = int(request.args.get('videoDuration'))

    transcript_df = dataRetriever.get_transcript(video_id)
    dataRetriever.get_comments(video_id, video_duration)
    dataRetriever.get_video_predict_timestamp_model(video_id, transcript_df)

    return json.dumps({"message": f'videoId [{video_id}] done init'})


@app.route("/api/comment")
def get_comment_value():
    video_id = request.args.get('videoId')
    video_duration = int(request.args.get('videoDuration'))
    comment_text = request.args.get('commentText')
    print(
        f'get_comment_value: videoId=[{video_id}], videoDuration=[{str(video_duration)}], commentText=[{comment_text}]')

    sentiment_data, jump_to_second_data = generate_comment_data(video_id, video_duration, comment_text)
    return json.dumps({
        "sentiment": sentiment_data,
        "jumpToSec": jump_to_second_data
    })


@app.route("/api/chart")
def get_chart_value():
    video_id = request.args.get('videoId')
    video_duration = int(request.args.get('videoDuration'))
    print(f'get_chart_value: videoId=[{video_id}], videoDuration=[{str(video_duration)}]')

    label_data, bad_data, meh_data, good_data = generate_chart_data(video_id, video_duration)
    return json.dumps({
        "label": label_data,
        "bad": bad_data,
        "meh": meh_data,
        "good": good_data
    })


def generate_comment_data(video_id, video_duration, video_comment):
    sentiment_data = predict_comment_sentiment(video_comment)
    jump_to_second_data = predict_comment_time(video_comment, video_id, dataRetriever.get_transcript(video_id),
                                               video_duration)
    return sentiment_data, jump_to_second_data


def generate_chart_data(video_id, video_duration):
    buckets = generate_buckets(video_duration)

    comments_df = dataRetriever.get_comments(video_id, video_duration)
    for index, comment in comments_df.iterrows():
        if comment.time is not None:
            for bucket in buckets:
                if bucket['start'] <= comment.time < bucket['end']:
                    bucket[comment.sentiment_cat] += 1
                    break

    label_data = [bucket['time'] for bucket in buckets]
    bad_data = [bucket['bad'] for bucket in buckets]
    meh_data = [bucket['meh'] for bucket in buckets]
    good_data = [bucket['good'] for bucket in buckets]

    return label_data, bad_data, meh_data, good_data


def generate_buckets(video_duration):
    return [{
        'time': get_time_str_from_seconds(i * video_duration / CHART_NUM_DATA_POINTS),
        'start': i * video_duration / CHART_NUM_DATA_POINTS,
        'end': (i + 1) * video_duration / CHART_NUM_DATA_POINTS,
        'good': 0,
        'meh': 0,
        'bad': 0
    }
        for i in range(CHART_NUM_DATA_POINTS)
    ]


def predict_comment_time(comment: str, video_id, transcript_df, video_duration) -> int:
    if IS_DUMMY_DATA:
        video_timestamp = random.randrange(video_duration)
    else:
        df_transcript_grp, instance, documents = \
            dataRetriever.get_video_predict_timestamp_model(video_id, transcript_df)
        video_timestamp = model_predict_video_segment \
            .predict_comment_timestamp(comment, df_transcript_grp, instance, documents)

    return video_timestamp


def predict_comment_sentiment(comment: str) -> float:
    return model_sentiment.get_text_sentiment(comment) if not IS_DUMMY_DATA else random.uniform(-1.0, 1.0)


def get_hours_unit_from_seconds(seconds) -> int:
    return int(seconds / (60 * 60))


def get_minutes_unit_from_seconds(seconds) -> int:
    seconds_in_hour = 60 * 60
    remaining_seconds_left = seconds % seconds_in_hour
    return int(remaining_seconds_left / 60)


def get_seconds_unit_from_seconds(seconds) -> int:
    return int(seconds % 60)


def get_time_str_from_seconds(seconds) -> str:
    if seconds >= 60 * 60:
        # Time in HH:MM:SS format
        return str(get_hours_unit_from_seconds(seconds)) + ':' + \
               str(get_minutes_unit_from_seconds(seconds)).zfill(2) + ':' + \
               str(get_seconds_unit_from_seconds(seconds)).zfill(2)
    else:
        # Time in MM:SS format
        return str(get_minutes_unit_from_seconds(seconds)) + ':' + \
               str(get_seconds_unit_from_seconds(seconds)).zfill(2)
