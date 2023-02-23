import sys
import os
import pickle
sys.path.append('/Users/clemens/repositories/movie_releases')

from db import db
from crawler import webcrawling
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S')

def run_etl():
    
    # Connect to MongoDB
    logging.info('Connecting to MongoDB...')
    mongo_db = db.connect_to_movie_collection()
    
    # Define providers and countries covered
    providers = ['Netflix', 'Amazon Prime Video', 'Disney Plus', 'Apple TV+']
    countries = ['Germany']
    
    # Scrape current releases
    logging.info('Start webscraping...')
    #clean_movie_list = webcrawling.scrape_current_releases(countries, providers)
    clean_movie_list = pickle.load(open('clean_movie_list.pickle', 'rb'))
    
    # Create bulk upsert request list
    request_list = db.create_bulk_upsert(clean_movie_list)
    
    # Upsert data into MongoDB
    number_movies = len(request_list)
    if number_movies > 0:
        logging.info(f'Upserting {len(request_list)} movies into MongoDB...')
        bulk_write_result= mongo_db.bulk_write(request_list, ordered=False)
        logging.info(f'Upserted {bulk_write_result.upserted_count} documents, {bulk_write_result.matched_count} were already in the DB.')
    else:
        logging.info('No new movies found.')
    
    
    return


if __name__ == '__main__':
    run_etl()