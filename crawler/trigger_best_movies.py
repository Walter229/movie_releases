import webcrawling
import sys, os
import logging
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from DB import crud


def trigger():
    logging.basicConfig(
    filename=os.environ.get('full_path') + '/logging/logger_best_movies.txt',
    filemode='a',
    format='%(asctime)s %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S')
    try:
        providers = ['Netflix', 'Amazon Prime Video']
        countries = ['Germany']
        best_movie_df = webcrawling.scrape_top_releases(countries=countries, providers=providers)
        crud.upload_movies_from_dataframe(best_movie_df)
        
        # Add logging
        logging.info('All good!')
        
    except Exception as e:
        exception_message = str(e)
        logging.info(f'Exception encountered: {exception_message}\n')

if __name__ == '__main__':
    trigger()