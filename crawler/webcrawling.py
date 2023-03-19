from selenium import webdriver
from bs4 import BeautifulSoup
import re
import time 
from pyshadow.main import Shadow
import datetime
import pandas as pd
import mappings
import logging
import os

# Selenium modules
from selenium.webdriver.common.action_chains import ScrollOrigin
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException



def xpath_soup(element):

    """
    Generate xpath from BeautifulSoup4 element.
    :param element: BeautifulSoup4 element.
    :type element: bs4.element.Tag or bs4.element.NavigableString
    :return: xpath as string
    :rtype: str
    """
    
    components = []
    child = element if element.name else element.parent
    for parent in child.parents:  # type: bs4.element.Tag
        siblings = parent.find_all(child.name, recursive=False)
        components.append(
            child.name if 1 == len(siblings) else '%s[%d]' % (
                child.name,
                next(i for i, s in enumerate(siblings, 1) if s is child)
                )
            )
        child = parent
    components.reverse()
    return '/%s' % '/'.join(components)

def check_exists_by_xpath(xpath, driver):
    """
    Helper function that checks whether an element exists on the page
    """
    try:
        driver.find_element(By.XPATH, xpath)
    except NoSuchElementException:
        return False
    return True

def get_timeline_links(driver, days_backwards=1):
    """Gets the movie links from the timeline for todays + days in the past as specified

    Args:
        soup (obj): beatufulsoup from justwatch html
        driver (obj): chromedriver

    Returns:
        dict: dictionary with dates as key and link lists as values
    """
    
    # Defines dates
    today = datetime.date.today().isoformat()
    dates = [today]
    for i in range(days_backwards):
        t = i+1
        date_minus_t = (datetime.date.today() - datetime.timedelta(days=t)).isoformat()
        dates.append(date_minus_t)
    
    # Get HTML page
    html = driver.page_source
    soup = BeautifulSoup(html, features="html.parser")
    
    # initialize movie dict
    movie_dict = {}
    
    # Get all timelines
    for n,time_line in enumerate(soup.findAll('div', class_='provider-timeline')):
        
        # Check if date from timeline matches input date
        timeline_date = re.search('(\d{4}-\d{2}-\d{2})',time_line.find_parent('div')['class'][-1]).group(1)
        if timeline_date in dates:
            date = timeline_date
            item_scrollbar = time_line.find('div', class_='hidden-horizontal-scrollbar__items')
            num_movies = int(re.search('(\d+)',time_line.text).group(1))
            
            # Get scroll-right element and scroll to the right until all moviel are loaded
            scrollbar_xpath = xpath_soup(item_scrollbar)
            scrollbar_driver = driver.find_element(By.XPATH,scrollbar_xpath)
            scroll_origin = ScrollOrigin.from_element(scrollbar_driver)
            action = webdriver.ActionChains(driver)
            action.scroll_from_origin(scroll_origin,1920,0).perform()
            
            movie_links = []
            all_movies_covered = False
            
            fail_counter = 0
            while not all_movies_covered:
                # Add all movie links available
                for movie in time_line.findAll('div', class_='horizontal-title-list__item'):
                    try:
                        rel_link = movie.find("a", recursive=False)['href']
                        full_link = 'https://www.justwatch.com' + rel_link
                        movie_links.append(full_link)
                    except:
                        fail_counter += 1

                # Check if all movies covered - if not scroll further
                if len(movie_links) + fail_counter >= num_movies:
                    all_movies_covered=True
                else:
                    movie_links = []
                    movie_xpath = xpath_soup(movie) # use last movie as scroll origin
                    movie_driver = driver.find_element(By.XPATH,movie_xpath)
                    scroll_origin = ScrollOrigin.from_element(movie_driver)
                    action = webdriver.ActionChains(driver)
                    action.scroll_from_origin(scroll_origin,1920,0).perform()
                    
                    # Reload html after scrolling
                    html = driver.page_source
                    soup = BeautifulSoup(html, features="html.parser")
                    time_line = soup.findAll('div', class_='provider-timeline')[n]
                    
            # Add links with date key
            movie_dict[date] = movie_links
    
    return movie_dict

def extract_movie_details_from_link(link, driver, date):
    driver.get(link)
    html = driver.page_source
    soup = BeautifulSoup(html, features="html.parser")
    
    movie_detail_dict = {}
    date_added = date
    
    # Extract movie information, if available
    try:
        name = soup.find('div', class_='title-block').find('h1').text
    except:
        name = ''
    try:
        release_year = soup.find('div', class_='title-block').find('span').text
    except:
        release_year = ''
    try:
        imdb_link = soup.find('div', attrs={'v-uib-tooltip': 'IMDB'}).next_element.get('href')
    except:
        imdb_link = ''
    try:
        imdb_rating = soup.find('div', attrs={'v-uib-tooltip': 'IMDB'}).text
    except:
        imdb_rating = ''
    try:
        runtime = soup.find('div', text='Laufzeit').next_sibling.text
    except:
        runtime = ''
    
    # Get all flatrate streaming links 
    try:
        streaming_links= (soup.find('div', class_='price-comparison--block')
                        .find_all('div', class_='presentation-type price-comparison__grid__row__element__icon'))
        flatrate_links = []
        for link in streaming_links:
            if 'Flat' in link.text:
                href = link.next.get('href')
                flatrate_links.append(href)
    except:
        flatrate_links = []
                
    # Fill movie detail dict
    movie_detail_dict['date_added'] = date_added
    movie_detail_dict['name'] = name
    movie_detail_dict['release_year'] = release_year
    movie_detail_dict['imdb_link'] = imdb_link
    movie_detail_dict['imdb_rating'] = imdb_rating
    movie_detail_dict['runtime'] = runtime
    movie_detail_dict['flatrate_links'] = flatrate_links
    
    return movie_detail_dict

def extract_movie_details(movie_link_dict, driver):
    """Scrapes movie detail pages and extracts movie information

    Args:
        movie_link_dict (dict): Dictionary containing the movie links for each date

    Returns:
        dict: Dictionary containing the movie details for each date
    """
    movies_detail_dict = {}
    
    
    for date, links in movie_link_dict.items():
        
        # Set-up list to store detail dicts for all movies of one date
        movies_detail_dict[date] = []
        
        # Open detail pages of the movies
        for link in links:
            movie_detail_dict = extract_movie_details_from_link(link, driver, date)
                        
            # Append to movies detail dict
            movies_detail_dict[date].append(movie_detail_dict)
    
    return movies_detail_dict

def remove_referral(link, driver):
    """Remove referral link by opening link and extracting the goal link.

    Args:
        link (str): Link with referral part
        driver (webdriver): chrome driver instance

    Returns:
        new_url(str): Clean link without referral part
    """
    
    # Open link provided
    driver.get(link)
    new_url = driver.current_url
    
    # Check if new url is different from old one (max 10 tries, else return old url)
    counter = 0
    while new_url == link and counter < 10:
        time.sleep(1)
        new_url = driver.current_url
        counter += 1
    
    return new_url

def reduce_to_one_link(link_list, country, provider):
    """Reduces link list to one final link, removes any links not from the provider.
    If no link provided, a default link for a provider is returned.

    Args:
        link_list (list): List of links
        country (str): country of link list provided
        provider (str): provider of link list provided

    Returns:
        final_link (str): Link to movie or default link for provider
    """
    
    from mappings import provider_slugs, default_link_dict
    
    # If link list is empty, add default link
    if not link_list:
        link_list = [default_link_dict[country][provider]]
    
    # Keep only links from provider
    provider_slug = provider_slugs[provider]
    updated_link_list = [link for link in link_list if provider_slug in link]
    
    # Keep first link from final list 
    # TODO: Black list some channel variants if needed(?)
    final_link = updated_link_list[0]
    
    return final_link

def clean_movie_data(movie_detail_dict, driver, country, provider, from_existing=False):
    """Cleans scraped movie data columns

    Args:
        movie_detail_dict (dict): Raw movie dictionary

    Returns:
        pd.DataFrame: Cleaned movie dataframe
    """
    # Combine results from all dates
    if from_existing:
        full_df = pd.DataFrame(movie_detail_dict.values())
    else:
        full_df = pd.concat([pd.DataFrame.from_dict(x) for x in movie_detail_dict.values()]).reset_index(drop=True)
    
    ##  Clean columns
    # Strip whitespaces from name column
    full_df['name'] = full_df['name'].str.strip()
    
    # Remove parentheses from release year column
    full_df['release_year'] = full_df['release_year'].str.extract(r'(\d{4})').apply(pd.to_numeric, errors='coerce')
    
    # Remove referal part from imdb link
    full_df['imdb_link'] = full_df['imdb_link'].str.replace(r'\/\?ref_=justwatch','', regex=True)
    
    # Add number of ratings column
    full_df['num_ratings'] = full_df['imdb_rating'].str.extract(r'\((.*)\)')
    
    # Remove numer of ratings from rating column
    full_df['imdb_rating'] = full_df['imdb_rating'].str.replace(r'\(.*\)', '', regex=True).apply(pd.to_numeric, errors='coerce')
    
    # Add empty string if no links found
    full_df['flatrate_links'] = full_df['flatrate_links'].apply(lambda x: x if x else x.append(''))
    
    # Remove referral part from streaming link
    full_df = full_df.loc[~(full_df['flatrate_links'].isna())]
    full_df['flatrate_links'] = full_df['flatrate_links'].apply(lambda x: [remove_referral(n, driver) for n in x])
    
    # Reduce to one link
    full_df ['flatrate_link'] = full_df['flatrate_links'].apply(lambda x: reduce_to_one_link(x, country, provider))
    
    return full_df

def handle_consent_popup(driver):
    """Handles consent pop-up

    Args:
        driver (selenium.webdriver): active webdriver instance
        
    Returns:
        None
    """
    
    time.sleep(5)
    shadow = Shadow(driver)
    try:
        accept_all = shadow.find_elements('button')[-1]
        accept_all.click()
    except NoSuchElementException:
        pass
    except ElementNotInteractableException:
        pass
    
    return

def set_up_chromedriver():
    options = Options()
    options.add_argument('--headless')  

    # Set-Up global Chromedriver
    chromedriver_path = os.environ.get('full_path') + '/crawler/chromedriver'
    driver = webdriver.Chrome(chromedriver_path, options=options)
    
    return driver

def scrape_current_releases(countries, providers, days_backwards=1):
    
    """ Scrapes the current releases of all countries and providers

    Args:
        countries (list): List of countries that releases should be scraped for. The corresponding
        streaming provider links need to be specified in the mappings file.
        providers (list): List of providers that releases should be scraped for. The corresponding 
        streaming links need to be specified in the mappings file.
        days_backwards (int): Number of days in the past to consider
    
    Returns:
        list: List of dictionaries containing the scraped movies
    """
    
    driver = set_up_chromedriver()
        
    # Loop over all countries and providers
    country_provider_movies = []
    for country in countries:
        logging.debug (f'Scraping {country}...')
        
        for provider in providers:
            logging.debug (f'Scraping {provider}...')
            
            # Get url from mapping file
            url = mappings.country_provider_dict[country][provider]
    
            # Open url with Chromedriver
            driver.get(url)
            
            # Handle consent cookies, click on accept all button
            handle_consent_popup(driver)
            
            # Get movie links from yesterday and today
            movie_link_dict = get_timeline_links(driver, days_backwards=days_backwards)
            
            # Check if any movies were found
            if len(movie_link_dict) > 0:
                 
                # Extract movie details
                movie_detail_dict = extract_movie_details(movie_link_dict, driver)
                
                # Clean movie details
                clean_movie_df = clean_movie_data(movie_detail_dict, driver, country, provider)
                
                # Convert df to dict
                clean_movie_list = clean_movie_df.to_dict('records')

                # Add meta data about provider and country and append to list
                for movie in clean_movie_list:
                    movie['meta_provider'] = provider
                    movie['meta_country'] = country
                    country_provider_movies.append(movie)
        
    return country_provider_movies

def scroll_down_page(driver, movies=500):
    """Scroll down page until n movies are found

    Args:
        driver (_type_): _description_

    Returns:
        _type_: _description_
    """
    
    SCROLL_PAUSE_TIME = 0.5

    # Get HTML page
    html = driver.page_source
    soup = BeautifulSoup(html, features="html.parser")
    
    # Get all movies currently shown:
    num_movies_shown = len(soup.findAll('div', class_='title-list-grid__item'))
    tries = 0
    
    while num_movies_shown < movies and tries < 50:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)
        
        # Get HTML page
        html = driver.page_source
        soup = BeautifulSoup(html, features="html.parser")
        
        # Get all movies currently shown:
        num_movies_shown = len(soup.findAll('div', class_='title-list-grid__item'))
        logging.debug(f"Try {tries+1}, found {num_movies_shown} movies...")
        tries += 1
    
    return driver

def filter_by_number_ratings(movie_dict, min_ratings=10000):
    for key in movie_dict.keys():
        # Extract number of ratings from imdb rating & convert to int
        movie_dict[key]['num_ratings'] = re.findall(r'\((.*)\)', movie_dict[key]['imdb_rating'])
        if movie_dict[key]['num_ratings']:
            movie_dict[key]['num_ratings'] = movie_dict[key]['num_ratings'][0]
            movie_dict[key]['num_ratings_int'] = int(movie_dict[key]['num_ratings'].replace('k', '000').replace('m','000000'))
        else:
            movie_dict[key]['num_ratings_int'] = 0
            
    # Only keep movies with at least 10k reviews
    filtered_dict = {k:v for (k,v) in movie_dict.items() if v['num_ratings_int'] > min_ratings}
    
    return filtered_dict

def get_best_movie_details(driver, num_movies, country, provider):
    import numpy as np
    
    best_movies = []
    # Scroll down page until 500 movies are shown
    scroll_down_page(driver, num_movies)
    
    # Get HTML page
    html = driver.page_source
    soup = BeautifulSoup(html, features="html.parser")
    movies = soup.findAll('div', class_='title-list-grid__item')
    
    movie_detail_dict = {}
    # Ensure that 3 proper movies are selected (movies with too few ratings are bing discarded)
    while len(movie_detail_dict) < 3:
        # Randomly select 3 movies to scrape
        random_nums = [np.random.randint(0,len(movies)) for i in range(3)]
        selected_movies = [movies[i] for i in random_nums]
        
        # Extract movie links
        movie_links = ['https://www.justwatch.com' + movie.find("a", recursive=False)['href'] for movie in selected_movies]

        # Get movie details from movie page
        date = datetime.date.today().strftime("%Y-%m-%d")
        for link in movie_links:
            movie_details = extract_movie_details_from_link(link, driver, date)
            movie_detail_dict[link] = movie_details
        
        # Filter out any movies with less than 10.000 ratings
        movie_detail_dict = filter_by_number_ratings(movie_detail_dict, min_ratings=10000)
        
    # Clean movie detail columns
    best_movie_df = clean_movie_data(movie_detail_dict, driver, country, provider,True)

    return best_movie_df

def scrape_top_releases(countries, providers):
    
    # Intantiate chromedriver
    driver = set_up_chromedriver()

    combined_best_movie_df = pd.DataFrame()
    for country in countries:
        
        for provider in providers:
            logging.debug (f'Scraping top releases from {provider} in {country}...')
            
            # Get url from mapping file
            url = mappings.country_provider_topmovies_dict[country][provider]
    
            # Open url with Chromedriver
            driver.get(url)
            
            # Handle consent cookies, click on accept all button
            handle_consent_popup(driver)
            
            # Scrape best movies
            best_movie_df =  get_best_movie_details(driver, 500, country, provider)
            best_movie_df['meta_provider'] = provider
            best_movie_df['meta_country'] = country
            combined_best_movie_df = pd.concat([combined_best_movie_df, best_movie_df])          
            
    return combined_best_movie_df

