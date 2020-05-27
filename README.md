# Wiki-Bacon

This project aims to replicate sixdegreesofwikipedia.com. This draws from the idea of [six degrees of separation](https://en.wikipedia.org/wiki/Six_degrees_of_separation), wherein any two people in the world are within six social connections (e.g. family, friends, colleagues) from each other.

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
