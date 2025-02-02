import datetime
import time

import pandas as pd

from google.cloud import bigquery
from google.cloud import storage
from google.cloud.exceptions import Forbidden, NotFound, TooManyRequests

from Product_Insights.Classification.utils \
        import keywords_based_classifier
from Product_Insights.Classification.create_classification_table \
        import create_keywords_map
from Product_Insights.Classification.upload_keywords_map \
        import upload_keywords_map
from Product_Insights.Sentiment.utils \
        import gc_detect_language, gc_sentiment, discretize_sentiment
from Product_Insights.Twitter.create_twitter_tables \
        import create_twitter_sentiment

#local_keywords_file = './Product_Insights/Classification/keywords_map.tsv'

bq_client = bigquery.Client()
storage_client = storage.Client()

def get_timeperiod(OUTPUT_DATASET, OUTPUT_TABLE):
  ''' Return the current time and last time data was previously saved with this script. 

  If the output table doesn't exists, then a new table is created with the same name
  and the returned start date is set as  2010-05-01. 
  '''
  start_dt = datetime.datetime(2010, 5, 1).isoformat()
  end_dt = datetime.datetime.now().isoformat()
  
  qry_max_date = ("SELECT max(created_at) max_date FROM {0}.{1}")\
                   .format(OUTPUT_DATASET, OUTPUT_TABLE)

  query_job = bq_client.query(qry_max_date)
  try:
    max_date_result = query_job.to_dataframe() 
  except NotFound:
    create_twitter_sentiment(OUTPUT_DATASET, OUTPUT_TABLE)
    query_job = bq_client.query(qry_max_date)
    max_date_result = query_job.to_dataframe() 

  max_date = pd.to_datetime(max_date_result['max_date'].values[0])
  if max_date is not None:
    start_dt = max_date.isoformat()
  return(start_dt, end_dt)

def load_data(INPUT_DATASET, INPUT_TABLE, start_dt, end_dt, limit=None):
  '''Gets data from the input table'''
  query = ('''SELECT * FROM `{0}.{1}` \
              WHERE `created_at` > TIMESTAMP("{2}") AND `created_at` <= TIMESTAMP("{3}") \
              ORDER BY `created_at` ASC''').\
              format(INPUT_DATASET, INPUT_TABLE, start_dt, end_dt)
  if limit:
    query += ' LIMIT {}'.format(limit)
  try:
      df = bq_client.query(query).to_dataframe()
      return(df)
  except Exception as e:
      print(e)
      return(None)

def language_analysis(df):
  """ Adds language and confidence to df using the Google Could Language API

  Note that the function can sometimes run into rate-limit restrictions, which is why
  the calls are wrapped in a while loop, to ensure that the API is called for all rows.
  """
  d_lang = {}
  d_confidence = {}
  for i, row in df.iterrows():
    while True:
      try:
          confidence, language = gc_detect_language(row.full_text)
          d_lang[row.id_str] = language
          d_confidence[row.id_str] = confidence
      except (Forbidden, TooManyRequests) as e:
        print(e)
        print('Waiting 100 seconds due to rate-limit constraint')
        time.sleep(100)
        continue
      break


  df[u'language'] = df['id_str'].map(d_lang)
  df[u'confidence'] = df['id_str'].map(d_confidence)
  return(df)

def filter_language(df, lang='en', lang_confidence=0.8):
  """ Filters non-english content
  
  Note that if there is no data left, the function implicitly returns None"""

  df = df[(df.language == lang)&(df.confidence >= lang_confidence)]
  df = df.drop(['language', 'confidence'], axis=1)
  if df.empty:
    print('No data in dataframe after language filter')
  return(df)

def run_sentiment_analysis(df):
  """ Adds score, magnitude and discrete_sentiment to df using the Google Could Sentiment API

  Note that the function can sometimes run into rate-limit restrictions, which is why
  the calls are wrapped in a while loop, to ensure that the API is called for all rows.
  """

  sentiment_score = {}
  sentiment_magnitude = {}
  for i, row in df.iterrows():
    while True:
      try:
        text = row.full_text
        score, magnitude = gc_sentiment(text)
        sentiment_score[row.id_str] = score
        sentiment_magnitude[row.id_str] = magnitude
      except (Forbidden, TooManyRequests) as e:
        print(e)
        print('Waiting 100 seconds due to rate-limit constraint')
        time.sleep(100)
        continue
      break


  df[u'score'] = df['id_str'].map(sentiment_score)
  df[u'magnitude'] = df['id_str'].map(sentiment_magnitude)

  df[u'discrete_sentiment'] = df.apply(lambda x: \
                             discretize_sentiment(x['score'],x['magnitude']), axis=1)  

  return(df)

def get_keywords_map(OUTPUT_DATASET, OUTPUT_BUCKET, local_keywords_file):
  '''Load the keywords map for use in determine_topics

  This functions matches the content of the OUTPUT_DATASET.table_name bq table
  with the content of the local_keywords_file. If these do not match then it overwrites
  the content of the bq table, otherwise it just uses the table as is. 
  '''


  table_name = 'keywords_map'
  query = 'SELECT * FROM `{0}.{1}`'.format(OUTPUT_DATASET, table_name)
  query_job = bq_client.query(query)
  try:
    keywords_map = query_job.to_dataframe() 
  except NotFound:
    create_keywords_map(OUTPUT_DATASET, table_name)
    upload_keywords_map(OUTPUT_BUCKET, local_keywords_file, OUTPUT_DATASET, table_name)
    query_job = bq_client.query(query)
    keywords_map = query_job.to_dataframe()

  # Test if local keywords file matches bq table, if not overwrite table 
  local_keywords_map = pd.read_csv(local_keywords_file, sep='\t')  
  if not local_keywords_map.equals(keywords_map):
    upload_keywords_map(OUTPUT_BUCKET, local_keywords_file, table_name)
    query_job = bq_client.query(query)
    keywords_map = query_job.to_dataframe()

  return(keywords_map)

def determine_topics(df, keywords_map):
  '''Determines the topic based on the keywords in keywords_map'''
  text_topic = {}
  
  #Detect topic based on keywords
  for i, row in df.iterrows():
    topics = keywords_based_classifier(row.full_text, keywords_map)

    #To enable writing our list of topics to a big query table
    #each topic has to be contained within a list of dicts
    #where each dicts key is topic and item is the topic at hand. 
    topics_list = [{'topic': ''}]
    for topic in topics:
      topics_list.append({'topic': topic})

    text_topic[row.id_str] = topics_list

  df[u'topics'] = df['id_str'].map(text_topic)
  return(df)


def update_bq_table(uri, fn, table_ref, table_schema):
  '''Saves data from a bq bucket to a table'''

  job_config = bigquery.LoadJobConfig()
  job_config.write_disposition = "WRITE_APPEND"
  job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
  
  #job_config.autodetect = True
  job_config.autodetect = False
  job_config.schema = table_schema
  
  orig_rows =  bq_client.get_table(table_ref).num_rows

  load_job = bq_client.load_table_from_uri(uri + fn, table_ref, job_config=job_config)  # API request
  print("Starting job {}".format(load_job.job_id))

  load_job.result()  # Waits for table load to complete.
  destination_table = bq_client.get_table(table_ref)
  print('Loaded {} rows into {}:{}.'.format(destination_table.num_rows-orig_rows, 'sumo', table_ref.table_id))

  
def move_blob_to_processed(bucket,fn):
  blob = bucket.blob("twitter/" + fn)
  new_blob = bucket.rename_blob(blob, "twitter/processed/" + fn)

def save_results(OUTPUT_DATASET, OUTPUT_TABLE, OUTPUT_BUCKET, df, start_dt, end_dt):
  '''Saves the dataframe to a gs bucket and a bq table'''

  bucket = storage_client.get_bucket(OUTPUT_BUCKET)
  dataset_ref = bq_client.dataset(OUTPUT_DATASET)
  table_ref = dataset_ref.table(OUTPUT_TABLE)

  fn = 'twitter_sentiment_' + start_dt[0:10] + "_to_" + end_dt[0:10] + '.json'
  uri = "gs://{}/twitter/".format(bucket.name)

  df.apply(lambda x: x.dropna(), axis=1).to_json('/tmp/'+fn,  orient="records", lines=True,date_format='iso')

  blob = bucket.blob("twitter/" + fn)
  blob.upload_from_filename("/tmp/" + fn)

  s = [
       bigquery.SchemaField("user_id", "INTEGER"),
       bigquery.SchemaField("topics", "RECORD", mode="REPEATED", fields=[bigquery.SchemaField("topic", "STRING", mode="NULLABLE"),], ),
       bigquery.SchemaField("score", "FLOAT"),
       bigquery.SchemaField("magnitude", "FLOAT"),
       bigquery.SchemaField("created_at", "TIMESTAMP"),
       bigquery.SchemaField("discrete_sentiment", "STRING"),
       bigquery.SchemaField("in_reply_to_status_id_str", "FLOAT"),
       bigquery.SchemaField("full_text", "STRING"),
       bigquery.SchemaField("id_str", "INTEGER"),
      ]
  update_bq_table(uri, fn, table_ref, s) 
  move_blob_to_processed(bucket,fn)


def get_unprocessed_data(OUTPUT_DATASET, OUTPUT_TABLE, INPUT_DATASET, INPUT_TABLE):
  start_dt, end_dt = get_timeperiod(OUTPUT_DATASET, OUTPUT_TABLE)
  df = load_data(INPUT_DATASET, INPUT_TABLE, start_dt, end_dt)
  return(df, start_dt, end_dt)

def get_sentiment(df):
  df = language_analysis(df)
  df = filter_language(df)
  if df is not None:
    df = run_sentiment_analysis(df)
  return(df)

def get_topics(OUTPUT_DATASET, OUTPUT_BUCKET, df, local_keywords_file):
  keywords_map = get_keywords_map(OUTPUT_DATASET, OUTPUT_BUCKET, local_keywords_file)
  df = determine_topics(df, keywords_map)
  return(df)

def process_data(INPUT_DATASET, INPUT_TABLE, OUTPUT_DATASET, OUTPUT_TABLE, OUTPUT_BUCKET, local_keywords_file):
  df, start_dt, end_dt = get_unprocessed_data(OUTPUT_DATASET, OUTPUT_TABLE, INPUT_DATASET, INPUT_TABLE)
  if not df.empty:
    df = get_sentiment(df)
  if df is not None:
    df = get_topics(OUTPUT_DATASET, OUTPUT_BUCKET, df, local_keywords_file)
    save_results(OUTPUT_DATASET, OUTPUT_TABLE, OUTPUT_BUCKET, df, start_dt, end_dt)
