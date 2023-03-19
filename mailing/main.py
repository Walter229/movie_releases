import sys
import os
sys.path.append(os.environ.get('full_path'))
from mailing import send_mails
from mailing import create_mails
import logging
from os import environ



def main(admin=False):
    # Define logging
    logging.basicConfig(filename=os.environ.get('full_path') + '/logging/logger_mail.txt',
                    filemode='a',
                    format='%(asctime)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)
    
    # Get all mail adresses to send the newsletter to
    if admin:
        mail_adresses = [os.environ.get('admin_mail')]
    else:
        mail_adresses = send_mails.get_mailing_list()
    
    # Fill newsletter template with movies
    template = open(os.environ.get('full_path') + "/templates/newsletter_template.html", "r").read()
    updated_template = create_mails.update_newsletter_template(template)
    
    # Prepare mail
    for mail_address in mail_adresses:
        from_email = environ.get('mail_from')
        to_email = mail_address
        subject = 'Check out this week\'s top movie releases 🍿'
        mail = send_mails.create_mail_str(from_email, to_email, subject, updated_template)
        try:
            response = send_mails.send_mail(to_email, mail)
            logging.info(f'Mail succesfully delivered to {mail_address}!')
        except:
            logging.info(f'Mail could not be sent to {mail_address}!')
    return

if __name__ == '__main__':
    main(admin=False)