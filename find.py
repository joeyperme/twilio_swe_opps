#!/usr/bin/env python3

import requests, time, signal, sys, re, html
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import schedule, time
from twilio.rest import Client

TIMEOUT = 5

media = set()

options = Options()
options.binary_location = "/usr/bin/chromium-browser"
options.add_argument("--headless")
driver = webdriver.Chrome(chrome_options=options)

keywords = {"software engineer", "security engineer"}
blacklist = {"sr.", "senior", "staff", "principal"}
locations = ["san francisco", "mountain view", "atlanta", "denver", "new york city", "redwood city", "remote"]

sent = set()

token = None
sid = None
phone_no = None
twilio_no = None

# read in account details
with open('/usr/local/secrets/twilio_sid') as inf:
    sid = inf.read().replace("\n", "", 1)
with open('/usr/local/secrets/twilio_tok') as inf:
    token = inf.read().replace("\n", "", 1)
with open('/usr/local/secrets/phone_no') as inf:
    phone_no = inf.read().replace("\n", "", 1)
with open('/usr/local/secrets/twilio_no') as inf:
    twilio_no = inf.read().replace("\n", "", 1)

def getPositionsGreenhouse(company):
    positions = []

    global driver, TIMEOUT, keywords, blacklist
    driver.get("about:blank")
    base = "https://boards.greenhouse.io"
    url = f"{base}/{company}/"
    driver.get(url)

    # let entire page load
    time.sleep(TIMEOUT)
    # get source
    html_source = driver.page_source

    # company not on greenhouse
    if "can't find that page" in html_source:
        return []


    # get openings
    soup = BeautifulSoup(html_source, 'html.parser')
    openings = soup.find_all("div", {"class": "opening"})

    for opening in openings:
        opening_name = opening.find("a")
        opening_lower = opening_name.text.lower()

        # filter on blacklist
        if any([ak in opening_lower for ak in blacklist]):
            continue

        if any([k in opening_lower for k in keywords]):
            link = opening.find("a")["href"]
            categories = opening.find("span").text
            positions.append(f"{opening_name.text},{categories} [https://boards.greenhouse.io{link}]")
            # print(f"[G] {company}: {opening_name.text} ({categories}) [{base}{link}]")

    return positions

def filterLocations(positions):

    rtn = []

    for pos in positions:
        pos = pos.lower()
        if any([loc in pos for loc in locations]):
            rtn.append(pos)

    return rtn


def sendPositions(positions):
    client = Client(sid, token)

    for pos in positions:
        # send it
        message = client.messages.create(
            body=pos,
            from_=twilio_no,
            to=phone_no,
        )

        # notch it
        sent.add(pos)

    if len(positions) < 1:
        message = client.messages.create(
            body="Nothing today; will check tomorrow morning! :)",
            from_=twilio_no,
            to=phone_no,
        )

def getAndSend(company):
    print("Running.")

    # get positions for company
    positions = getPositionsGreenhouse(company)

    # filter them by desired locations (US)
    positions = filterLocations(positions)

    # filter positions sent already
    positions = [pos for pos in positions if pos not in sent]
    
    # send and notch the rest
    sendPositions(positions)

#getAndSend("twilio")
schedule.every().day.at("8:00").do(getAndSend, "twilio")
minute = 60
while True:
    schedule.run_pending()
    time.sleep(10)

