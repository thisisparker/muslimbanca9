#!/usr/bin/env python3

import json, os, requests, yaml
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

def twitter_upload(image_list):
    media_ids = []

# Debug print statement
#    print("Here's the list I'm going to try " + str(image_list))

    for image in image_list:
        res = requests.get(image)
        res.raise_for_status()

# Another debug print statement
#        print("Uploading " + image)

        uploadable = BytesIO(res.content)

        response = twitter.upload_media(media=uploadable)
        media_ids.append(response['media_id'])

# One more debug print statement
#    print("Media IDs: " + str(media_ids))

    return media_ids

# Deprecated image fetching code, to be replaced with
# above technique once I get it working

#def get_image(url):
#    pdf = requests.get(url)
#    pdf.raise_for_status()

#    all_pages = image.Image(blob=pdf.content)
#    single = all_pages.sequence[0]
#    image_io = BytesIO()

#    with image.Image(single) as i:
#        i.format = 'png'
#        i.background_color = color.Color('white')
#        i.alpha_channel = 'remove'
#        i.save(image_io)

#    image_io.seek(0)

#    return image_io

# End deprecated code

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
        newrow['url'] = link.get('href')
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
                    dc_url = doc.canonical_url
                    dc_images = doc.normal_image_url_list
#                    if len(dc_images) <= 4:
#                        media_ids = twitter_upload(dc_images)
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
