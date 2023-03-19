import sys
import os
sys.path.append(os.environ.get('full_path'))
import pandas as pd
from datetime import datetime, timedelta
from pymongo import MongoClient
from DB import crud
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()

def connect_to_movie_collection():
    # Connect to MovieReleases mongoDB
    uri = os.environ.get('database_uri')
    cert_path = os.environ.get('database_cert_path')
    client = MongoClient(uri,
                        tls=True,
                        tlsCertificateKeyFile=cert_path)
    
    db = client['movieReleases']
    collection = db['movies']
    
    return collection

def get_all_entries(collection):
    
    # Get all entries from MongoDB
    all_entries = collection.find()
    all_entry_df = pd.DataFrame(list(all_entries))
    
    return all_entry_df

def get_top_movies_by_provider(n_movies=3):
    
    # Read in all movie releases from MongoDB
    movie_collection = connect_to_movie_collection()
    movie_df = get_all_entries(movie_collection)
    movie_df['date_added'] = pd.to_datetime(movie_df['date_added'])
    
    # Filter for last week
    today = datetime.today()
    one_week_ago = today - timedelta(days=7)
    last_week_movie_df = movie_df[movie_df['date_added'] >= one_week_ago]
    
    # Filter out movies without imdb score or reviews
    last_week_movie_df = last_week_movie_df.dropna(subset=['imdb_rating', 'num_ratings'])
    
    # Only keep movies with at least 10k reviews
    last_week_movie_df['num_ratings'] = last_week_movie_df['num_ratings'].str.replace('k', '000').str.replace('m','000000').astype(int)
    last_week_movie_df = last_week_movie_df[last_week_movie_df['num_ratings'] >= 10000]
    
    # Store release year as int
    last_week_movie_df['release_year'] = last_week_movie_df['release_year'].astype(int, errors='ignore')
    
    # Sort movies by rating and split by streaming service
    sorted_movies = last_week_movie_df.sort_values(by=['imdb_rating'], ascending=False)
    top_movies_by_service = sorted_movies.groupby('meta_provider').head(n_movies).reset_index()
    
    # Split df by streaming service and convert to dict
    top_movie_dict = {}
    for service in top_movies_by_service['meta_provider'].unique():
        provider_df = top_movies_by_service[top_movies_by_service['meta_provider'] == service]
        provider_df = provider_df[['name', 'release_year', 'runtime', 'imdb_rating', 'flatrate_links', 'flatrate_link']]
        top_movie_dict[service] = provider_df.to_dict('records')
    
    return top_movie_dict

def insert_mail_content(soup, movie_dict):
    
    # Only keep netflix and amazon
    movie_dict = {k:v for (k,v) in movie_dict.items() if k in ['Amazon Prime Video', 'Netflix']}
        
    provider_list = movie_dict.keys()
    
    for provider in provider_list:
        
        top_movies = movie_dict[provider]
        
        # Find associated table
        provider_table = soup.find('table', {'id':f'{provider} table'})
        for top_n, row in enumerate(top_movies):
            # Add new row
            new_row = soup.new_tag('tr')
            
            # Add name (add asterix if top movie)
            name = soup.new_tag('td')
            name.string = str(movie_dict[provider][top_n]['name'])
            if 'top_movie' in row.keys():
                # Add asterisk
                asterisk = soup.new_tag("sup",attrs={"class": "asterisk"})
                asterisk.string = "*"
                name.append(asterisk)
                
                # Add disclamer
                disclaimer = soup.find('div', {'class': 'asterisk_placeholder'})
                disclaimer.string = "Added from provider's existing library as not enough good movies were released this week"
                asterisk_disclaimer = soup.new_tag("sup")
                asterisk_disclaimer.string = "*"
                disclaimer.insert(0, asterisk_disclaimer)
                
            # Add rating
            rating = soup.new_tag('td')
            rating.string = str(movie_dict[provider][top_n]['imdb_rating'])
            
            # Add release year
            release = soup.new_tag('td')
            release.string = str(movie_dict[provider][top_n]['release_year'])
            
            # Add runtime
            runtime = soup.new_tag('td')
            runtime.string = str(movie_dict[provider][top_n]['runtime'])
            
            # Add link
            link = soup.new_tag('td')
            link_a = soup.new_tag('a', href=str(movie_dict[provider][top_n]['flatrate_link']))
            link_a.string = 'Link'
            link.append(link_a)

            # Add all columns to row and row to table
            new_row.append(name)
            new_row.append(rating)
            new_row.append(release)
            new_row.append(runtime)
            new_row.append(link)
            provider_table.append(new_row)
    
    return soup

def fill_with_best_movies(movie_dict, provider, num_missing):
    
    # Get top movies, sort for latest ones from provider that have not been sent yet
    top_movies = crud.get_all_movies()
    top_movies['date_added'] = pd.to_datetime(top_movies['date_added'])
    top_movies_filtered = top_movies.loc[(top_movies['sent']==False) & (top_movies['meta_provider']==provider)]
    top_movies_filtered = top_movies_filtered.sort_values(by=['date_added']).iloc[:num_missing,]
    top_movies_filtered['top_movie'] = True
    
    # Convert to list of dicts
    top_movies_filtered = top_movies_filtered[['name', 'release_year', 'runtime', 'imdb_rating', 'flatrate_link', 'top_movie']]
    top_movie_list = top_movies_filtered.to_dict('records')
    movie_dict[provider] += top_movie_list
    
    # Sort movie dict by imdb rating
    movie_dict[provider] = sorted(movie_dict[provider], key=lambda d: float(d['imdb_rating']), reverse=True) 
    
    return movie_dict

def update_newsletter_template(template):
    """ Run template updating pipeline

    Args:
        template (str): Template html

    Returns:
        updated_template(str): Template with inserted new movies
    """
    # Get recent top movies
    n_movies = 3
    top_movie_dict = get_top_movies_by_provider(n_movies=n_movies)
    
    # Check if each provider got 3 movies, else fill with best movies
    providers_used = ['Amazon Prime Video', 'Netflix']
    for provider in providers_used:
        if not provider in top_movie_dict.keys():
            top_movie_dict[provider] = []
            top_movie_dict = fill_with_best_movies(top_movie_dict, provider, n_movies)
        if len(top_movie_dict[provider]) < n_movies:
            num_missing_movies = n_movies - len(top_movie_dict[provider])
            top_movie_dict = fill_with_best_movies(top_movie_dict, provider, num_missing_movies)
    
    # Update email template with recent top movies
    soup = BeautifulSoup(template,features="html.parser")
    new_soup = insert_mail_content(soup, top_movie_dict)
    updated_template = new_soup.prettify(formatter='html')
    
    return updated_template

