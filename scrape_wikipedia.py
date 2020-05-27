from bs4 import BeautifulSoup
import requests
import queue
import mysql.connector as connector

def toWikiLink(string):
    string = string.strip().replace(" ", "_")
    return "https://en.wikipedia.org/wiki/" + string

cnx = connector.connect(user='root',
                        host='127.0.0.1',
                        database='separation')
cursor = cnx.cursor()

start = "Hydrophobia_(disambiguation)"
cursor.execute("INSERT INTO page (title) VALUES (%s)", (start,))
cnx.commit()
start_id = cursor.lastrowid

scanned = set()
added = set()
q = queue.Queue()

q.put(start_id)
added.add(start_id)
currCount = 0

while not q.empty():
    id = q.get()
    if id in scanned:
        continue
    currCount += 1
    
    cursor.execute("SELECT title FROM page WHERE id = %s", (id,))
    title = cursor.fetchone()[0]

    page = requests.get(toWikiLink(title))
    scanned.add(id)
    print("Running (" + str(currCount) + "): " + title)

    if page.status_code != 200:
        print("---------Error: page " + title + " cannot be accessed. Status code: " + str(page.status_code))
        continue

    soup = BeautifulSoup(page.content, 'html.parser')
    tags = soup.find(id="bodyContent").find_all('a')
    
    added_links = set()
    for tag in tags:
        link = tag.get("href", "")
        if not link.startswith("/wiki/") or link.startswith("/wiki/File"):
            continue
        
        link = link[6:]
        if link in added_links:
            continue
        added_links.add(link)
        print("    > Adding edge: " + link)
        
        cursor.execute("SELECT id FROM page WHERE title = %s", (link,))
        row = cursor.fetchone()
        if row:
            new_id = row[0]
        else:
            cursor.execute("INSERT INTO page (title) VALUES (%s)", (link,))
            new_id = cursor.lastrowid
            cnx.commit()
        
        if new_id not in added:
            q.put(new_id)
            added.add(new_id)
        
        cursor.execute("INSERT INTO link (source, destination) VALUES (%s, %s)", (id, new_id,))
        new_id = cursor.lastrowid
        cnx.commit()

cursor.close()
cnx.close()