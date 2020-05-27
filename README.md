# Wiki-Bacon

This project aims to replicate [sixdegreesofwikipedia.com](https://www.sixdegreesofwikipedia.com/). This draws from the idea of [six degrees of separation](https://en.wikipedia.org/wiki/Six_degrees_of_separation), wherein any two people in the world are within six social connections (e.g. family, friends, colleagues) from each other.

Instead of people, this project aims to find what the minimum number of clicks is to get from any page on Wikipedia to any other page on Wikipedia. Please note that only articles (i.e. does not include files, images, external links) on the English version of Wikipedia (https://en.wikipedia.org/) will be considered for this project.

The main goal of this project is for the code author to be able to learn how to handle the collection and analysis of large amounts of data.

## Setup
We will be using the [request](https://requests.readthedocs.io/en/master/), [Connector/Python](https://dev.mysql.com/doc/connector-python/en/connector-python-example-connecting.html), and [BeautfiulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) libraries.
```
python -m pip install requests
python -m pip install mysql.connector
python -m pip install beautifulsoup4
```

### Attempt 1: Scraping the Wikipedia website and storing data in a database

After going through a few articles, it was apparent that the URLs for each article started with https://en.wikipedia.org/wiki/ and was simply followed by the title of the article.

The idea was to (1) start from any article on Wikipeda, (2) scrape the article (using BeautifulSoup) for all links starting with https://en.wikipedia.org/wiki/, (3) add those links to a list, and (4) keep going through the list until all articles have been visited once.

If all articles are, in fact, reachable from any other article, then there shouldn't be a problem with this _eventually_ getting all the data.

All the IDs and title for articles (i.e. nodes) were stored in a `page` table in the database, while all links coming from each page (i.e directed edges) were stored in a `link` table. The process of database creation was as follows.

``` sql
CREATE DATABASE separation;
ALTER DATABASE separation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE separation;

CREATE TABLE page (
    id      INT NOT NULL UNIQUE AUTO_INCREMENT PRIMARY KEY,
    title   VARCHAR(255) NOT NULL
);
CREATE TABLE link (
    source          INT NOT NULL,
    destination     INT NOT NULL,

	FOREIGN KEY(source) REFERENCES page(id),
	FOREIGN KEY(destination) REFERENCES page(id)
);
```
NOTE: [Altering the character set](https://stackoverflow.com/questions/6115612/how-to-convert-an-entire-mysql-database-characterset-and-collation-to-utf-8) for the database to `utf8mb4` was done as a need to account for the articles that had special characters.

One very obvious and critical problem that immediately came up was the very slow speed of the program. Not only did the program have to make a request for each article, but each response came with a lot of information that was not needed (e.g. Wikipedia navigation, article content). Even after that, the program had to scrape the response for the links, which may or may not have led to a Wikipedia article.

This approach simply could not run efficiently and accurately as it was slow and prone to collecting incorrect information.

### Attempt 2: Pulling data from the [MediaWiki API](https://www.mediawiki.org/wiki/API:Main_page).

Note that the actual API endpoint used is specifically for the English Wikipedia site: https://en.wikipedia.org/w/api.php

Upon looking through the API documentation, it was apparent that there were two sets of endpoint parameters that were ideal to obtain the data I needed for this project. (Since all that is being done is querying for data, then `action` parameter should be set to `query`.)

The first one is for querying all the pages available on the website by setting [`list=allpages`](https://en.wikipedia.org/w/api.php?action=help&modules=query%2Ballpages). The actual parameters used are shown below. Moving through the list was made possible by setting `apcontinue` to the `apcontinue` value returned by each request.
``` json
{
    "action": "query",
    "format": "json",
    "list": "allpages",
    "apnamespace": "0",
    "apfilterredir": "nonredirects",
    "aplimit": "max"
}
```
[Check it out here.](https://en.wikipedia.org/w/api.php?action=query&format=json&list=allpages&apnamespace=0&apfilterredir=nonredirects&aplimit=max)

The second one is for querying the redirects and links leading to each page, which can be done by setting [`prop=linkshere`](https://en.wikipedia.org/w/api.php?action=help&modules=query%2Blinkshere). The actual parameters used are shown below. Sometimes, it takes more than one request to obtain all the redirects and links leading to a page. Moving through the list was made possible by setting `lhcontinue` to the `lhcontinue` value returned by each request, when applicable.
``` json
{
    "action": "query",
    "format": "json",
    "prop": "linkshere",
    "pageids": 2327951,
    "lhprop": "pageid|title|redirect",
    "lhnamespace": "0",
    "lhlimit": "max"
}
```
[Check it out here.](https://en.wikipedia.org/w/api.php?action=query&format=json&prop=linkshere&pageids=2327951&lhprop=pageid%7Ctitle%7Credirect&lhnamespace=0&lhlimit=max)

For the first set of parameters, there was no problem with the speed of the requests. Even with a slow 1.5 Mbps download connection, it only took around 6 hours to get the IDs and titles for all the articles. The bigger problem was mostly due to the slow database insertion.

#### Attempt 2.1: Extended Inserts
As a way to speed up the program, I looked online and found this [article](https://medium.com/@benmorel/high-speed-inserts-with-mysql-9d3dcd76f723) which talked about **extended inserts** being faster than individual inserts. The code was modified to do this bulk insertion and it was indeed faster, but still not fast enough. It was fine for the first hundred thousand entries or so, but it seems that the time it took for each insert to finish increased as more entries were stored in the table.

#### Attempt 2.2: Threading
In the way that things were going, the program had to 1) make a request, 2) wait to get back the response, 3) start inserting the data into the database, 4) wait for insertion to complete, and then 5) start making another request again.

The problem with this approach is that there's a lot of waiting. More specifically, the program would be stuck inserting data into the database when it could be starting a new request instead. This was because the program was running the requests and the database insertions all in the same thread.

To avoid this, a separate [thread](https://stackoverflow.com/questions/3044580/multiprocessing-vs-threading-python) was created for the database inserts while the request creation process was kept in the main thread. This did speed things up, but the bottleneck of slow database inserts was still a problem.

#### Attempt 2.2: `LOAD DATA INFILE`
Instead of inserting data into the database during runtime, the program was modified to instead print the data out into a file **in a specific format** which can later be written into the database.

The idea was to get the generated file and pass it in as a parameter into [`LOAD DATA INFILE`](https://dev.mysql.com/doc/refman/8.0/en/load-data.html).

In order to do this, I did some research on what the file should look like and found the "opposite" of `LOAD DATA INFILE` which was [`SELECT ... INTO`](https://dev.mysql.com/doc/refman/8**.0/en/select-into.html), which simply generates a TSV file.

Since `LOAD DATA INFILE` takes in parameters for the way the file is formatted, the program was modified to print out a CSV file, which would later be put into the database using the following command.
``` sql
LOAD DATA INFILE 'pull_nonredirect_pages_out.txt'
INTO TABLE test
FIELDS ENCLOSED BY '"'
TERMINATED BY ','
ESCAPED BY '"'
LINES TERMINATED BY '\r\n';
```
NOTE: The string used for terminating lines would [vary](https://stackoverflow.com/questions/3821784/whats-the-difference-between-n-and-r-n) depending on the operating system used.

This proved to be the fastest and most convenient way to put the entries into the database, taking only 35 minutes to insert more than six million two-column rows into the database.

The task of getting the IDs and titles for all articles has already been completed. The only remaining data points that must be obtained are the redirects and links to the said articles (i.e. the "edges" of our graph).

A program was created to go through the IDs printed in the already generated file and to query for the redirects and links to them. Since each API call could only return the redirects and links for one article ID at a time, more than six million requests would have to be made. Looking through the logs printed out by the program in realtime, it seemed that approximately three requests were made every second. This means that it would take more than 23 days to get the data for all six million articles.

For a project that doesn't need realtime updating, a 23-day wait isn't all that bad to get all the data. Despite this, there is still a key problem with this process of data collection: the Wikipedia database, and thus the API, gets updated during this 23-day period. That is to say that pages may be renamed, removed, or have links leading to and from them changed while the rest of the data is being collected.

After the 23 days, it's very likely that the data points collected would have conflicts with each other. Perhaps it would be better to get a dump of Wikipedia's database and obtain the desired data from it.
