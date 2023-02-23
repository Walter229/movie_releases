import pandas as pd
import sys
from datetime import datetime, timedelta
import requests


# Import local modules
sys.path.append('/Users/clemens/repositories/movie_releases')
from db import db
from mailing import create_mail

def get_top_movies_by_provider(n_movies=3):
    
    # Read in all movie releases from MongoDB
    movie_collection = db.connect_to_movie_collection()
    movie_df = db.get_all_entries(movie_collection)
    movie_df['date_added'] = pd.to_datetime(movie_df['date_added'])
    
    # Filter for last week
    today = datetime.today()
    one_week_ago = today - timedelta(days=7)
    last_week_movie_df = movie_df[movie_df['date_added'] >= one_week_ago]
    
    # Filter out movies without imdb score or reviews
    last_week_movie_df = last_week_movie_df.dropna(subset=['imdb_rating', 'num_ratings'])
    
    # Only keep movies with at least 10k reviews
    last_week_movie_df['num_ratings'] = last_week_movie_df['num_ratings'].str.replace('k', '000').astype(int)
    last_week_movie_df = last_week_movie_df[last_week_movie_df['num_ratings'] >= 10000]
    
    # Sort movies by rating and split by streaming service
    sorted_movies = last_week_movie_df.sort_values(by=['imdb_rating'], ascending=False)
    top_movies_by_service = sorted_movies.groupby('meta_provider').head(n_movies).reset_index()
    
    # Split df by streaming service and convert to dict
    top_movie_dict = {}
    for service in top_movies_by_service['meta_provider'].unique():
        provider_df = top_movies_by_service[top_movies_by_service['meta_provider'] == service]
        provider_df = provider_df[['name', 'release_year', 'runtime', 'imdb_rating', 'flatrate_links']]
        top_movie_dict[service] = provider_df.to_dict('records')
    
    return top_movie_dict

def convert_ref_links(links):
    #TODO implement
    # Open links in list and return new html link as string
    for link in links:
        html = requests.get(link)
        new_link = html.url
    return

def main():
    
    # Get top movies
    top_movie_dict = get_top_movies_by_provider(n_movies=3)
    
    # Send mail
    create_mail.create_mail(top_movie_dict)
    
    
    return top_movie_dict

if __name__ == '__main__':
    main()
