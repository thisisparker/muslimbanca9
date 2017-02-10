#!/usr/bin/env python3

import json, os, requests, time, urllib, yaml
from bs4 import BeautifulSoup
from documentcloud import DocumentCloud
from io import BytesIO
from twython import Twython

fullpath = os.path.dirname(os.path.realpath(__file__))
CONFIG = os.path.join(fullpath, "config.yaml")

def get_config():
    with open(CONFIG,'r') as c:
        config = yaml.load(c)
    return config

def set_twitter(config):
    twitter_app_key = config['twitter_app_key']
    twitter_app_secret = config['twitter_app_secret']
    twitter_oauth_token = config['twitter_oauth_token']
    twitter_oauth_token_secret = config['twitter_oauth_token_secret']
    return Twython(twitter_app_key, twitter_app_secret, twitter_oauth_token, twitter_oauth_token_secret)

def set_test_twitter(config):
    twitter_app_key = config['test_app_key']
    twitter_app_secret = config['test_app_secret']
    twitter_oauth_token = config['test_oauth_token']
    twitter_oauth_token_secret = config['test_oauth_token_secret']
    return Twython(twitter_app_key, twitter_app_secret, twitter_oauth_token, twitter_oauth_token_secret)

def set_documentcloud(config):
    dc_user = config['documentcloud_user']
    dc_pw = config['documentcloud_pw']
    return DocumentCloud(dc_user,dc_pw)

def twitter_upload(twitter, image_list):
    media_ids = []

    for image in image_list:
        try:
            res = requests.get(image)
            res.raise_for_status()

            uploadable = BytesIO(res.content)

            response = twitter.upload_media(media=uploadable)
            media_ids.append(response['media_id'])
        except:
            pass

    return media_ids

def shorten_name(name):
    if len(name) > 95:
        return name[:94] + "…"
    else:
        return name

def main():
    config = get_config()
    twitter = set_twitter(config)

# Comment out the above and comment in the below for live testing
# action
#    twitter = set_test_twitter(config)

    dc = set_documentcloud(config)
    saved_path = os.path.join(fullpath, "lastcheck.json")

    res = requests.get("https://www.ca9.uscourts.gov/content/view.php?pk_id=0000000860")
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html5lib")

    div = soup.find(id="ci_pe")
    rows = div.findAll("tr")[1:]
    sanrows = [r for r in rows if r.get_text(strip=True)]

    table = list()

    for row in sanrows:
        newrow = dict()
        cells = row.findAll("td")
    
        newrow['date'] = cells[0].get_text()

        link = cells[1].find('a')
        if link == None:
            continue
        newrow['url'] = urllib.parse.urljoin("http://",
            link.get('href'))
        newrow['name'] = cells[1].get_text()

        table.append(newrow)
    
    if os.path.exists(saved_path):
        with open(saved_path,"r") as f:
            saved_table = json.load(f)

        for item in table:
            saved_item = next((s for s in saved_table 
                if s['url'] == item['url']),None)

            if saved_item == None:
                media_ids = []
                short_name = shorten_name(item['name'])

                

                if item['url'][-4:].lower() == ".pdf":
                    doc = dc.documents.upload(item['url'],
                        title=item['name'],
                        published_url=item['url'],
                        access='public',
                        project="31541-Washington-v-Trump-Muslim-Ban-9th-Circuit")
                    doc = dc.documents.get(doc.id)

                    while doc.access != 'public':
                        doc = dc.documents.get(doc.id)
                        time.sleep(5)

                    dc_url = doc.canonical_url
                    if doc.pages <= 4:
                        dc_images = doc.normal_image_url_list
                        media_ids = twitter_upload(twitter,
                            dc_images)
                    status = ("New docket entry! " + short_name +
                        " " + dc_url)

                else:
                    status = ("New docket entry! " + short_name +
                        " " + item['url'])

                twitter.update_status(status=status,
                    media_ids=media_ids)

    with open(saved_path,"w") as f:
        json.dump(table,f)

if __name__ == "__main__":
    main()
