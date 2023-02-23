from selenium import webdriver
from bs4 import BeautifulSoup
import re
import time 
from pyshadow.main import Shadow
import datetime
import pandas as pd
from crawler import mappings
import logging

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

def get_timeline_links(driver):
    """Gets the movie links from the timeline for yesterday and today

    Args:
        soup (obj): beatufulsoup from justwatch html
        driver (obj): chromedriver

    Returns:
        dict: dictionary with dates as key and link lists as values
    """
    
    # Defines dates
    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    dates = [yesterday, today]
    
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
            
            while not all_movies_covered:
                # Add all movie links available
                for movie in time_line.findAll('div', class_='horizontal-title-list__item'):
                    rel_link = movie.find("a", recursive=False)['href']
                    full_link = 'https://www.justwatch.com' + rel_link
                    movie_links.append(full_link)

                # Check if all movies covered - if not scroll further
                if len(movie_links) >= num_movies:
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
                        
            # Append to movies detail dict
            movies_detail_dict[date].append(movie_detail_dict)
    
    return movies_detail_dict

def clean_movie_data(movie_detail_dict):
    """Cleans scraped movie data columns

    Args:
        movie_detail_dict (dict): Raw movie dictionary

    Returns:
        pd.DataFrame: Cleaned movie dataframe
    """
    # Combine results from all dates
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
    
    # TODO: Remove referral part from streaming link
    # full_df['flatrate_links'] = full_df['flatrate_links'].str.replace(re.escape('https://click.justwatch.com/a?r='),'')
    
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

def scrape_current_releases(countries, providers):
    
    """ Scrapes the current releases of all countries and providers

    Args:
        countries (list): List of countries that releases should be scraped for. The corresponding
        streaming provider links need to be specified in the mappings file.
        providers (list): List of providers that releases should be scraped for. The corresponding 
        streaming links need to be specified in the mappings file.
    
    Returns:
        list: List of dictionaries containing the scraped movies
    """
    
    options = Options()
    options.add_argument('--headless')  

    # Set-Up global Chromedriver
    driver = webdriver.Chrome(options=options)  
    action = webdriver.ActionChains(driver)
        
    # Loop over all countries and providers
    country_provider_movies = []
    for country in countries:
        logging.info (f'Scraping {country}...')
        
        for provider in providers:
            logging.info (f'Scraping {provider}...')
            
            # Get url from mapping file
            url = mappings.country_provider_dict[country][provider]
    
            # Open url with Chromedriver
            driver.get(url)
            
            # Handle consent cookies, click on accept all button
            handle_consent_popup(driver)
            
            # Get movie links from yesterday and today
            movie_link_dict = get_timeline_links(driver)
            
            # Check if any movies were found
            if len(movie_link_dict) > 0:
                 
                # Extract movie details
                movie_detail_dict = extract_movie_details(movie_link_dict, driver)
                
                # Clean movie details
                clean_movie_df = clean_movie_data(movie_detail_dict)
                
                # Convert df to dict
                clean_movie_list = clean_movie_df.to_dict('records')

                # Add meta data about provider and country and append to list
                for movie in clean_movie_list:
                    movie['meta_provider'] = provider
                    movie['meta_country'] = country
                    country_provider_movies.append(movie)
        
    return country_provider_movies


