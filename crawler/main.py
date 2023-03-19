import sys
import os
sys.path.append(os.environ.get('full_path'))

from crawler import db
from crawler import webcrawling
import logging

# Configure logging


def run_etl(days_backwards=1):
    
    logging.basicConfig(
    filename=os.environ.get('full_path') + '/logging/logger_new_movies.txt',
    filemode='a',
    format='%(asctime)s %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S')
    
    try:
        # Connect to MongoDB
        logging.debug('Connecting to MongoDB...')
        mongo_db = db.connect_to_movie_collection()
        
        # Define providers and countries covered
        providers = ['Netflix', 'Amazon Prime Video', 'Disney Plus', 'Apple TV+']
        countries = ['Germany']
        
        # Scrape current releases
        logging.debug('Start webscraping...')
        clean_movie_list = webcrawling.scrape_current_releases(countries, providers, days_backwards=days_backwards)
        
        # Create bulk upsert request list
        request_list = db.create_bulk_upsert(clean_movie_list)
        
        # Upsert data into MongoDB
        number_movies = len(request_list)
        if number_movies > 0:
            logging.debug(f'Upserting {len(request_list)} movies into MongoDB...')
            bulk_write_result= mongo_db.bulk_write(request_list, ordered=False)
            logging.debug(f'Upserted {bulk_write_result.upserted_count} documents, {bulk_write_result.matched_count} were already in the DB.')
        else:
            logging.debug('No new movies found.')

        # Add logging
        logging.info('All good!')
    
    #Write any exception to logging file
    except Exception as e:
        exception_message = str(e)
        logging.info(f'Exception encountered: {exception_message}\n')
        
    
    return


if __name__ == '__main__':
    run_etl(days_backwards=2)