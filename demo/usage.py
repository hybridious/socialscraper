import os, sys; sys.path.append(os.path.abspath('../'))

import pickle, logging, datetime
from socialscraper.facebook import FacebookScraper

from models import Session, FacebookUser
from lib import save_user

logging.basicConfig(level=logging.DEBUG)

session = Session()
scraper_type = "nograph"

if not os.path.isfile('facebook_scraper.pickle'):
    scraper = FacebookScraper(scraper_type=scraper_type)
    scraper.add_user(email=os.getenv('FACEBOOK_EMAIL'), password=os.getenv('FACEBOOK_PASSWORD'))
    scraper.login()
    scraper.init_api()
    pickle.dump(scraper, open('facebook_scraper.pickle', 'wb'))
else:
    scraper = pickle.load(open('facebook_scraper.pickle', 'rb'))
    scraper.scraper_type = scraper_type

# Example: Get members of Facebook Group - 357518484295082 (Northwestern)
for i, result in enumerate(scraper.graph_search(None, "members", 357518484295082)):
    save_user(result, session)

# # Example: Get friends of FacebookUser
# for i, result in enumerate(scraper.get_friends_nograph("andybayer")):
#     save_user(result, session)