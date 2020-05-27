from threading import Thread
import requests
import queue

import csv
import time
import logging

logging.basicConfig(filename="pull_links_and_redirects_log.txt", level=logging.DEBUG)

pageids_file = open("pull_nonredirect_pages_out.txt", newline="\n", encoding="utf-8")
csv_reader = csv.reader(pageids_file, delimiter=',')

link_file = open("pull_links_out.txt", "w", newline="\n", encoding="utf-8")
link_writer = csv.writer(link_file, delimiter=',')

redirect_file = open("pull_redirects_out.txt", "w", newline="\n", encoding="utf-8")
redirect_writer = csv.writer(redirect_file, delimiter=',')

q = queue.Queue()

printed_link_success_count = 0
printed_link_fail_count = 0
printed_redirect_success_count = 0
printed_redirect_fail_count = 0
def print_into_file():
    while True:
        page_links = q.get()
        pageid = page_links[0]
        links = page_links[1]
        actual_links = [link for link in links if not link[2]]
        redirects = [link for link in links if link[2]]
        
        if len(actual_links) != 0:
            print_links(pageid, actual_links)
        if len(redirects) != 0:
            print_redirects(pageid, redirects)
        q.task_done()

def print_links(pageid, links):
    global printed_link_success_count, printed_link_fail_count
    while True:
        try:
            link_text = ",".join([str(link[0]) for link in links])
            link_writer.writerow([pageid, link_text])
            link_file.flush()
            print()
            log_debug_message("Successfully printed ({}) links for: {}".format(len(links), pageid))
            printed_link_success_count += len(links)
            break
        except:
            log_error_message("Failed to print ({}) links for {}".format(len(links), pageid))
            printed_link_fail_count += len(links)
            time.sleep(5)
            continue
        
    log_debug_message("# of links succesfully printed: " + str(printed_link_success_count))
    log_debug_message("# of links failed to print: " + str(printed_link_fail_count))

def print_redirects(pageid, redirects):
    global printed_redirect_success_count, printed_redirect_fail_count
    while True:
        try:
            redirect_ids = [str(redirect[0]) for redirect in redirects]
            redirect_text = ",".join(redirect_ids)
            redirect_writer.writerow([pageid, redirect_text])
            redirect_file.flush()
            print()
            log_debug_message("Successfully printed ({}) redirects for: {}".format(len(redirects), pageid))
            printed_redirect_success_count += len(redirects)
            break
        except:
            print()
            log_error_message("Failed to print ({}) redirects for {}".format(len(redirects), pageid))
            printed_redirect_fail_count += len(redirects)
            time.sleep(5)
            continue
    log_debug_message("# of redirects succesfully printed: " + str(printed_redirect_success_count))
    log_debug_message("# of redirects failed to print: " + str(printed_redirect_fail_count))

def request_pages(pageid, lhcontinue=""):
    # https://en.wikipedia.org/w/api.php?action=query&format=json&
    # prop=linkshere&pageids=2327951&lhprop=pageid%7Ctitle%7Credirect
    # &lhnamespace=0&lhlimit=max
    base_url = "https://en.wikipedia.org/w/api.php"
    payload = {
        "action": "query",
        "format": "json",
        "prop": "linkshere",
        "pageids": pageid,
        "lhprop": "pageid|title|redirect",
        "lhnamespace" : "0",
        "lhlimit" : "max"
    }
    if lhcontinue != "":
        payload["lhcontinue"] = lhcontinue
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

succesful_request_count = 0
failed_request_count = 0
retrieved_link_count = 0

for row in csv_reader:
    curr_pageid = row[0]
    print("Reading: ({}) {}".format(curr_pageid, row[1]))
    lhcontinue = ""
    running_link_list = []

    while True:
        identifier = curr_pageid
        if lhcontinue != "":
            identifier += "|{}".format(lhcontinue)
        try:
            response = request_pages(pageid=curr_pageid, lhcontinue=lhcontinue)
        except:
            log_error_message("Failed request for " + identifier)
            failed_request_count += 1
            time.sleep(5)
            continue
        
        if not response or response.status_code != requests.codes.ok:
            log_error_message("Unsuccessful response retrieved for " + identifier)
            failed_request_count += 1
            time.sleep(5)
            continue
        
        print()
        log_debug_message("Successfully obtained response for " + identifier)
        succesful_request_count += 1

        log_debug_message("# of successful requests: " + str(succesful_request_count))
        log_debug_message("# of failed requests: " + str(failed_request_count))
        
        json = response.json()
        linkshere = json["query"]["pages"][curr_pageid]
        linkshere = linkshere["linkshere"] if "linkshere" in linkshere else []

        retrieved_link_count += len(linkshere)
        log_debug_message("# of links retrieved: " + str(retrieved_link_count))
        new_links = [(link["pageid"], link["title"], "redirect" in link) for link in linkshere]
        running_link_list.extend(new_links)
        
        if "continue" in json and "lhcontinue" in json["continue"]:
            lhcontinue = json["continue"]["lhcontinue"]
        else:
            q.put((curr_pageid, running_link_list))
            break

q.join() # Wait until the queue is done being processed.

print("Program has successfully completed.")