import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from email.header import Header
import mailchimp_marketing as MailchimpMarketing
from os import environ

def create_mail_str(mail_from, mail_to, subject, html_content):
    """Construct mail string from input variables and html content

    Args:
        mail_from (str): sender
        mail_to (str): receiver
        subject (str): subject 
        html_content (str): str content

    Returns:
        mail_string(str): Mail formatted as string
    """
    # Construct mail
    mail_message = MIMEMultipart()
    mail_message['From'] = formataddr((str(Header('MovieMail', 'utf-8')), mail_from))
    mail_message['To'] = mail_to
    mail_message['Subject'] = subject
    
    # Add body
    mail_message.attach(MIMEText(html_content, 'html'))
    
    # Convert to string
    mail_string = mail_message.as_string()
    
    return mail_string

def send_mail(receiver, mail_string):
    """Send mail via gmail

    Args:
        receiver (str): receiver mail adress
        mail_string (str): mail formatted as string
    """
    # Get environmental variables
    mail_pw = environ.get('gmail_key')
    
    # Connect with gmail server 
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        mail_from = environ.get('mail_from')
        server.login(mail_from, mail_pw)
        response = server.sendmail(mail_from, receiver, mail_string)
        return response
    
def get_mailing_list(list_id=''):
    api_key = environ.get('mailchimp_api_key')

    # Connect to client
    client = MailchimpMarketing.Client()
    client.set_config({"api_key": api_key,"server": "us21"})
    
    all_members = []
    # If list_id specified, get members from that list id
    if list_id:
        response = client.lists.get_list_members_info(list_id)
        for member in response['members']:
            all_members.append(member['email_address'])
    
    # Get all members from all lists
    else:
        response = client.lists.get_all_lists()
        for list in response['lists']:
            list_id = list['id']
            response = client.lists.get_list_members_info(list_id)
            for member in response['members']:
                all_members.append(member['email_address'])
                
    return all_members