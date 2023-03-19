from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base

# Define the database file path
database_file = 'top_movies.db'

# Create the SQLAlchemy engine
engine = create_engine(f'sqlite:///{database_file}', echo=True)

# Create a base class for declarative models
Base = declarative_base()


# Define your table model
class Movies(Base):
    __tablename__ = 'topMovies'

    # Define the columns and their data types
    id = Column(Integer, primary_key=True)
    date_added = Column(String)
    name = Column(String)
    release_year = Column(Integer)
    imdb_link = Column(String)
    imdb_rating = Column(String)
    runtime = Column(String)
    flatrate_link = Column(String)
    num_ratings = Column(String)
    meta_provider = Column(String)
    meta_country = Column(String)
    sent = Column(Boolean)

if __name__ == '__main__':
    # Create the database and tables
    Base.metadata.create_all(engine)