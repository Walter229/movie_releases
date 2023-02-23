import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError
import os
import logging
from bs4 import BeautifulSoup
import re

def insert_mail_content(soup, movie_dict):
    
    provider_list = movie_dict.keys()
    
    for provider in provider_list:
        
        # Find associated table
        provider_table = soup.find('table', {'id':f'{provider} table'})
        rows=provider_table.find_all('tr')
        for top_n, row in enumerate(rows[1:]):
            # For each row, replace content with movie info
            cols = row.find_all('td')
            cols[0].find(text=re.compile('.*')).replace_with(str(movie_dict[provider][top_n]['name']))
            cols[1].find(text=re.compile('.*')).replace_with(str(movie_dict[provider][top_n]['imdb_rating']))
            cols[2].find(text=re.compile('.*')).replace_with(str(movie_dict[provider][top_n]['release_year']))
            cols[3].find(text=re.compile('.*')).replace_with(str(movie_dict[provider][top_n]['runtime']))
            # Add link
            cols[4].find(text=re.compile('.*')).replace_with('Link')
            cols[4]['href'] = str(movie_dict[provider][top_n]['flatrate_links'][0])
    
    return soup

def create_mail(movie_dict):
    
    # Read in mailchimp config from env file
    api_key = os.environ.get('mailchimp_api_key')
    campaign_id = os.environ.get('mailchimp_campaign_id')
    
    # Set up client
    try:
        client = MailchimpMarketing.Client()
        client.set_config({
            "api_key": api_key,
            "server": "us21"
        })
    except ApiClientError as error:
        logging.error(f"Error: {error.text}")
        raise ValueError(error.text)
    
    # Get campaign content
    response = client.campaigns.get_content(campaign_id=campaign_id)
    html = response['html']
    
    # Adjust campaign html with movie info
    soup = BeautifulSoup(html, 'html.parser')
    adjusted_soup = insert_mail_content(soup, movie_dict)
    adjusted_html = str(adjusted_soup)
    
    # Open html file
    #path = '/Users/clemens/Desktop/campaign_mail.html 18-36-39-468.html'
    #HTMLFile = open("index.html", "r")
  
    # Reading the file
    #index = HTMLFile.read()
    response = client.campaigns.create({"type": "html"})
    
    # Send html to mailchimp
    try:
        response = client.campaigns.set_content(campaign_id, {'html': adjusted_html})
        print(response)
    except ApiClientError as error:
        logging.error(f"Error: {error.text}")
        raise ValueError(error.text)
    
    # Send campaign
    try:
        response = client.campaigns.send("campaign_id")
        print(response)
    except ApiClientError as error:
        logging.error(f"Error: {error.text}")
        raise ValueError(error.text)
    
    
    return