# New Movie release newsletter
This repository contains set-up of a service to provide information about the most recent movie releases on various streaming websites to subscribers of a newsletter. Every friday, the best movie releases of the week and some additional information about them is sent.

## ETL 
The data pipeline scrapes information about recently released movies from JustWatch.com, cleanes them and afterwards uploads them to a NoSql database.
This pipeline is controlled via Airflow and run daily.


## Website
A simple website is set up using Flask. Users can register for the newsletter and select the streaming providers that they want to get movie release information for.


