from time import sleep
import logging, lxml.html, json, urllib, re
from ...base import ScrapingError
from ..models import FacebookUser, FacebookPage

from ..import graphapi, public

logger = logging.getLogger(__name__)

SEARCH_URL = 'https://www.facebook.com/search'
AJAX_URL = 'https://www.facebook.com/ajax/pagelet/generic.php/BrowseScrollingSetPagelet'

def search(browser, current_user, graph_name, method_name, graph_id = None, api = None):
    """
    Facebook Graph Search Generator

    General Usage:

    for result in search(browser, current_user, graph_name, method_name):
        print result

    browser: authenticated requests session (see auth.py)
    current_user: authenticated user
    graph_name: name of Facebook graph object such as a user name or page name
    method_name: name of internal Facebook graph search methods;
                 list: 'pages-liked', 'likers', 'users-named'

    Example:

    for result in search(browser, current_user, "al.johri", "pages-liked"):
        print result

    for result in search(browser, current_user, "mightynest", "likers"):
        print result

    """

    def _find_script_tag(raw_html, phrase):
        doc = lxml.html.fromstring(raw_html)
        script_tag = filter(lambda x: x.text_content().find(phrase) != -1, doc.cssselect('script'))
        if not script_tag: return None
        return json.loads(script_tag[0].text_content()[24:-1])

    def _parse_ajax_data(raw_json):
        require = raw_json['jsmods']['require']
        tester = lambda x: x[0] == "BrowseScrollingPager" and x[1] == "init"
        data_parameter = map(lambda x: x[3][1], filter(tester, require))[0]
        return data_parameter

    def _parse_cursor_data(raw_json):
        if raw_json.get('error'): raise ScrapingError(raw_json.get('errorDescription'))
        require = raw_json['jsmods']['require']
        tester = lambda x: x[0] == "BrowseScrollingPager" and x[1] == "pageletComplete"
        cursor_parameter = map(lambda x: x[3][0], filter(tester, require))[0]
        return cursor_parameter

    def _parse_result(raw_html):
        doc = lxml.html.fromstring(raw_html)
        # import pdb; pdb.set_trace()
        # items = map(lambda x: (x.get('href'), x.text_content()), doc.cssselect('div[data-bt*=title]'))
        # items = doc.cssselect('div[data-bt*=title] > a')
        # for item in items:
        #     url = item.get('href')
        #     number_of_items = item.getparent().getparent().cssselect('div[data-bt*=snippets] > div>div ')[0].text_content()
            # print url, number_of_items

        # methods to get id
        # x.getparent().getparent().cssselect('.FriendRequestOutgoing')[0].get('data-profileid'))
        # 
        el_id = lambda x: json.loads(x.getparent().getparent().getparent().getparent().getparent().get('data-bt'))['id']
        return map(lambda x: (x.get('href'), x.text_content(), el_id(x)), doc.cssselect('div[data-bt*=title] > a'))

    def _get_payload(ajax_data, uid):
        return {
            'data': json.dumps(ajax_data), 
            '__user': uid, 
            '__a': 1, 
            '__req': 'a', 
            '__dyn': '7n8apij35CCzpQ9UmWOGUGy1m9ACwKyaF3pqzAQ',
            '__rev': 1106672
        }

    def _result_to_model(result, method_name):
        url = result[0]
        name = result[1]
        uid = result[2]
        # num_members = result[2]

        # print(url, name, num_members)

        # import pdb; pdb.set_trace()

        username = public.parse_url(url)

        # if api:
        #     uid, category = graphapi.get_attributes(api, username, ["id", "category"])
        # else:
        #     uid, category = public.get_attributes(username, ["id", "category"])


        if uid == None: 
            print "Couldn't find UID of %s" % username
            # raise ValueError("Couldn't find uid of %s" % username)

        uid = int(uid) if uid else None

        if method_name == "pages-liked":
            return FacebookPage(page_id=uid, username=username, url=url, name=name, type=category)
        elif method_name == "likers" or method_name == "friends":
            return FacebookUser(uid=uid, username=username, url=url, name=name)
        elif method_name == "groups":
            return (uid, url, name, category)
        else:
            raise ScrapingError("Wut kinda model is %. Check out da _result_to_model method" % method_name)

    # https://www.facebook.com/search/str/ruchi/users-named
    # https://www.facebook.com/search/str/ruchi/users-named/me/friends/intersect?ref=filter
    # https://www.facebook.com/search/str/ruchi/users-named/228401243342/students/intersect?ref=filter
    # https://www.facebook.com/search/str/ruchi/users-named/males/intersect?ref=filter
    # https://www.facebook.com/search/str/ruchi/users-named/females/intersect?ref=filter
    # https://www.facebook.com/search/str/ruchi/users-named/108641632493225/residents/present/intersect?ref=filter
    # https://www.facebook.com/search/str/ruchi/users-named/108659242498155/residents/present/intersect?ref=filter
    # https://www.facebook.com/search/str/ruchi/users-named/106517799384578/residents/present/intersect?ref=filter
    # https://www.facebook.com/search/str/ruchi/users-named/108007405887967/visitors/intersect
    def _graph_request(graph_id, method_name, post_data = None):
        if not post_data:
            response = browser.get(SEARCH_URL + "/%s/%s" % (graph_id, method_name))
            cursor_tag = _find_script_tag(response.text, "cursor")
            ajax_tag = _find_script_tag(response.text, "encoded_query")
            cursor_data = _parse_cursor_data(cursor_tag) if cursor_tag else None
            ajax_data = _parse_ajax_data(ajax_tag) if ajax_tag else None
            post_data = dict(cursor_data.items() + ajax_data.items()) if ajax_data and cursor_data else None

            current_results = []

            # Extract current_results from first page
            for element in lxml.html.fromstring(response.text).cssselect(".hidden_elem"): 
                comment = element.xpath("comment()")
                if not comment: continue
                element_from_comment = lxml.html.tostring(comment[0])[5:-4]
                doc = lxml.html.fromstring(element_from_comment)
                # import pdb; pdb.set_trace()
                # potentially num_members x.getparent().getparent().cssselect('div[class="_52eh"]')[0].text_content()
                # potentially data profile id 
                el_id = lambda x: json.loads(x.getparent().getparent().getparent().getparent().getparent().get('data-bt'))['id']
                current_results += map(lambda x: (x.get('href'), x.text_content(), el_id(x)), doc.cssselect('div[data-bt*=title] > a'))
        else:
            payload = _get_payload(post_data, current_user.id)
            response = browser.get(AJAX_URL + "?%s" % urllib.urlencode(payload))
            raw_json = json.loads(response.content[9:])
            raw_html = raw_json['payload']

            post_data = _parse_cursor_data(raw_json)
            current_results = _parse_result(raw_html)
        return post_data, current_results

    # Main Facebook Graph Search

    if not graph_id: graph_id = public.get_id(graph_name)
    post_data, current_results = _graph_request(graph_id, method_name)
    # import pdb; pdb.set_trace()
    for result in current_results: 
        try:
            yield _result_to_model(result, method_name)
        except ValueError:
            continue

    while post_data:
        current_post_data, current_results = _graph_request(graph_id, method_name, post_data)
        if current_post_data == None or current_results == None: break
        # print current_results
        for result in current_results: 
            try:
                yield _result_to_model(result, method_name)
            except ValueError:
                continue            
        post_data.update(current_post_data)