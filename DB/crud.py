# Function to retrieve all movies
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from DB.schema import Movies
import pandas as pd
from os import environ

# Define the database file path
database_file = environ.get('database_file')

# Create the SQLAlchemy engine
conn = f'sqlite:///{database_file}'
engine = create_engine(conn, echo=True)

# Create a session factory
Session = sessionmaker(bind=engine)

def get_all_movies():
    movies = pd.read_sql_table('topMovies', conn)
    return movies

def query_db(query):
    result = pd.read_sql_query(query, conn)
    return result

# function to upload movies from df
def upload_movies_from_dataframe(df):
    session = Session()
    movies = []
    for i, row in df.iterrows():
        movie = Movies(
            date_added=row['date_added'],
            name=row['name'],
            release_year=row['release_year'],
            imdb_link=row['imdb_link'],
            imdb_rating=row['imdb_rating'],
            runtime=row['runtime'],
            flatrate_link=row['flatrate_link'],
            num_ratings=row['num_ratings'],
            meta_provider=row['meta_provider'],
            meta_country=row['meta_country'],
            sent=False
        )
        movies.append(movie)
    session.add_all(movies)
    session.commit()
    session.close()