from pymongo import MongoClient
from pymongo.operations import UpdateOne
import os

def connect_to_movie_collection():
    # Connect to MovieReleases mongoDB
    uri = os.environ.get('database_uri')
    client = MongoClient(uri,
                        tls=True,
                        tlsCertificateKeyFile=os.environ.get('database_cert_path'))
    db = client['movieReleases']
    collection = db['movies']
    
    return collection

def create_bulk_upsert(clean_movie_list):
    
    # Create request list for bulk upsert
    request_list = []
    for movie in clean_movie_list:
        request_list.append(UpdateOne(
            filter= 
            {
            'date_added': movie['date_added'],
            'name': movie['name'],
            'imdb_link': movie['imdb_link'],
            'meta_provider': movie['meta_provider'],
            'meta_country': movie['meta_country'],
            }, 
            update={'$set': movie}, upsert=True))
    
    return request_list

def get_all_entries(collection):
    import pandas as pd
    
    # Get all entries from MongoDB
    all_entries = collection.find()
    all_entry_df = pd.DataFrame(list(all_entries))
    
    return all_entry_df