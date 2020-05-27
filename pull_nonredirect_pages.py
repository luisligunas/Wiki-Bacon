from threading import Thread
import requests
import queue

import csv
import time
import logging

logging.basicConfig(filename="pull_nonredirect_pages_log.txt", level=logging.DEBUG)

f = open("pull_nonredirect_pages_out.txt", "w", newline="\n", encoding="utf-8")
output_writer = csv.writer(f, delimiter=',')

q = queue.Queue()

printed_entry_success_count = 0
inserted_entry_fail_count = 0
def print_into_file():
    global printed_entry_success_count, inserted_entry_fail_count
    while True:
        entries = q.get()
        
        if entries != []:
            first_entry_debug_text = "({}) -> {}".format(str(entries[0][0]), entries[0][1])
            
            while True:
                try:
                    output_writer.writerows(entries)
                    f.flush()
                    print()
                    log_debug_message("Successfully printed ({}) entries starting at: {}".format(len(entries), first_entry_debug_text))
                    printed_entry_success_count += len(entries)
                    break
                except:
                    print()
                    log_error_message("Failed to print ({}) entries starting at {}".format(len(entries), first_entry_debug_text))
                    inserted_entry_fail_count += len(entries)
                    time.sleep(5)
                    continue
        
        log_debug_message("# of entries succesfully printed: " + str(printed_entry_success_count))
        log_debug_message("# of entries failed to print: " + str(inserted_entry_fail_count))
        q.task_done()

def request_pages(starting_title = "", redirects="all"):
    # https://en.wikipedia.org/w/api.php?action=query&format=json&list=allpages&
    # apnamespace=0&apfilterredir=nonredirects&aplimit=max
    base_url = "https://en.wikipedia.org/w/api.php"
    payload = {
        "action": "query",
        "format": "json",
        "list": "allpages",
        "apnamespace" : "0",
        "apfilterredir" : redirects,
        "aplimit" : "max",
        "apcontinue" : starting_title
    }
    response = requests.get(base_url, params=payload)
    return response

def log_error_message(message):
    logging.exception(message)
    print(message)

def log_debug_message(message):
    logging.debug(message)
    print(message)

for i in range(1):
    worker = Thread(target=print_into_file, args=())
    worker.setDaemon(True)
    worker.start()

starting_title = ""
succesful_request_count = 0
failed_request_count = 0
retrieved_entry_count = 0

while True:
    try:
        response = request_pages(starting_title=starting_title, redirects="nonredirects")
    except:
        log_error_message("Failed request for " + starting_title)
        failed_request_count += 1
        time.sleep(5)
        continue
    
    if not response or response.status_code != requests.codes.ok:
        log_error_message("Unsuccessful response retrieved for " + starting_title )
        failed_request_count += 1
        time.sleep(5)
        continue
    
    print()
    log_debug_message("Successfully obtained response for " + starting_title)
    succesful_request_count += 1

    log_debug_message("# of successful requests: " + str(succesful_request_count))
    log_debug_message("# of failed requests: " + str(failed_request_count))
    
    json = response.json()
    page_list = json["query"]["allpages"]

    retrieved_entry_count += len(page_list)
    log_debug_message("# of entries retrieved: " + str(retrieved_entry_count))
    q.put([(page["pageid"], page["title"]) for page in page_list])
    
    if "continue" not in json:
        break
    starting_title = json["continue"]["apcontinue"]

q.join() # Wait until the queue is done being processed.

print("Program has successfully completed.")