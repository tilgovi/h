from pyramid import renderers

import requests, json, types, re, operator
from datetime import datetime
from collections import defaultdict
from markdown import markdown
import urlparse

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode


class Hypothesis:

    def __init__(self, username=None, password=None):
        self.app_url = 'https://hypothes.is/app'
        self.api_url = 'https://hypothes.is/api'
        self.query_url = 'https://hypothes.is/api/search?{query}'
        self.anno_url = 'https://hypothes.is/a'
        self.via_url = 'https://via.hypothes.is'
        self.username = username
        self.password = password

    def login(self):
        # https://github.com/rdhyee/hypothesisapi 
        # pick up some cookies to start the session
        
        r = requests.get(self.app_url)
        cookies = r.cookies

        # make call to https://hypothes.is/app?__formid__=login
        
        payload = {"username":self.username,"password":self.password}
        self.csrf_token = cookies['XSRF-TOKEN']
        data = json.dumps(payload)
        headers = {'content-type':'application/json;charset=UTF-8', 'x-csrf-token': self.csrf_token}
        
        r = requests.post(url=self.app_url  + "?__formid__=login", data=data, cookies=cookies, headers=headers)
        
        # get token

        url = self.api_url + "/token?" + urlencode({'assertion':self.csrf_token})
        r = (requests.get(url=url,
                         cookies=cookies, headers=headers))
      
        self.token =  r.content

    def search(self):
        params = {'limit':200, 'offset':0 }

        while True:
            h_url = self.api_url.format(query=urlencode(params))
            r = requests.get(h_url).json()
            rows = r.get('rows')
            params['offset'] += len(rows)
            if len(rows) is 0:
                break
            for row in rows:
                yield row

    def create(self, url=None, start_pos=None, end_pos=None, prefix=None, 
               quote=None, suffix=None, text=None, tags=None):
        headers = {'Authorization': 'Bearer ' + self.token}
        payload = {
            "uri": url,
            "user": 'acct:' + self.username + '@hypothes.is',
            "permissions": {
                "read": ["group:__world__"],
                "update": ['acct:' + self.username + '@hypothes.is'],
                "delete": ['acct:' + self.username + '@hypothes.is'],
                "admin":  ['acct:' + self.username + '@hypothes.is']
                },
            "document": { },
            "target": 
            [
                {
                "selector": 
                    [
                        {
                        "start": start_pos,
                        "end": end_pos,
                        "type": "TextPositionSelector"
                        }, 
                        {
                        "type": "TextQuoteSelector", 
                        "prefix": prefix,
                        "exact": quote,
                        "suffix": suffix
                        },
                    ]
                }
            ], 
            "tags": tags,
            "text": text
        }
        data = json.dumps(payload)
        r = requests.post(self.api_url + '/annotations', headers=headers, data=data)
        return r

    def call_search_api(self, args={'limit':200}):
        h_url = Hypothesis().query_url.format(query=urlencode(args))
        s = requests.get(h_url).text.decode('utf-8')
        j = json.loads(s)
        return j

    def get_active_users(self):
        j = Hypothesis().call_search_api()
        users = defaultdict(int)
        rows = j['rows']
        for row in rows:
            info = self.get_info_from_row(row)
            user = info['user']
            users[user] += 1
        users = sorted(users.items(), key=operator.itemgetter(1,0), reverse=True)
        return users

    @staticmethod
    def friendly_time(dt):
        now = datetime.now()
        delta = now - dt

        minute = 60
        hour = minute * 60
        day = hour * 24
        month = day * 30
        year = day * 365

        diff = delta.seconds + (delta.days * day)

        if diff < 10:
            return "just now"
        if diff < minute:
            return str(diff) + " seconds ago"
        if diff < 2 * minute:
            return "a minute ago"
        if diff < hour:
            return str(diff / minute) + " minutes ago"
        if diff < 2 * hour:
            return "an hour ago"
        if diff < day:
            return str(diff / hour) + " hours ago"
        if diff < 2 * day:
            return "a day ago"
        if diff < month:
            return str(diff / day) + " days ago"
        if diff < 2 * month:
            return "a month ago"
        if diff < year:
            return str(diff / month) + " months ago"
        return str(diff / year) + " years ago"

    @staticmethod
    def get_info_from_row(r):
        updated = r['updated'][0:19]
        user = r['user'].replace('acct:','').replace('@hypothes.is','')
        uri = r['uri'].replace('https://via.hypothes.is/h/','').replace('https://via.hypothes.is/','')

        if r['uri'].startswith('urn:x-pdf') and r.has_key('document'):
            if r['document'].has_key('link'):
                links = r['document']['link']
                for link in links:
                    uri = link['href']
                    if uri.encode('utf-8').startswith('urn:') == False:
                        break
            if uri.encode('utf-8').startswith('urn:') and r['document'].has_key('filename'):
                uri = r['document']['filename']

        if r.has_key('document') and r['document'].has_key('title'):
            t = r['document']['title']
            if isinstance(t, types.ListType) and len(t):
                doc_title = t[0]
            else:
                doc_title = t
        else:
            doc_title = uri
        doc_title = doc_title.replace('"',"'")
        if doc_title == '': doc_title = 'untitled'

        tags = []
        if r.has_key('tags') and r['tags'] is not None:
            tags = r['tags']
            if isinstance(tags, types.ListType):
                tags = [t.strip() for t in tags]

        text = ''
        if r.has_key('text'):
            text = r['text']
        refs = []
        if r.has_key('references'):
            refs = r['references']
        target = []
        if r.has_key('target'):
            target = r['target']

        is_page_note = False
        if refs == [] and target == [] and tags == []: 
            is_page_note = True

        return {'updated':updated, 'user':user, 'uri':uri, 'doc_title':doc_title, 
                'tags':tags, 'text':text, 'references':refs, 'target':target, 'is_page_note':is_page_note }

    @staticmethod
    def make_tag_html(info):
        if len(info['tags']):
            tag_items = []
            for tag in info['tags']:
                tag_items.append('<li><span class="tag-item">%s</span></li>' % tag)
            return '<ul>%s</ul>' % '\n'.join(tag_items)
        else:
            return ''

    @staticmethod
    def make_quote_html(info):
        if len(info['target']) == 0:
               return ''
        uri = info['uri']
        selector = info['target'][0]['selector']
        quote = ''
        for sel in selector:
            if sel.has_key('exact'):
                quote = sel['exact']
        return quote

    @staticmethod
    def make_text_html(info):
        text = info['text']
        if info['is_page_note']:
            text = '<span title="Page Note" class="h-icon-insert-comment"></span> ' + text
        text = markdown(text)
        return text

    @staticmethod
    def make_references_html(info):
        anno_url = Hypothesis().anno_url
        references = info['references']
        if references is None or len(references) == 0:
            return ''
        assert( isinstance(references,types.ListType) )
        ref = references[0]
        html = """
<a onclick="javascript:embed_conversation('{ref}'); return false"  
   id="{ref}" 
   target="_new" 
   href="{anno_url}/{ref}">conversation</a>"""
        ref_html = html.format(anno_url=anno_url, ref=ref)
        return ref_html

class HypothesisUserActivity:

    def __init__(self,limit):
        self.uri_bundles = defaultdict(list)
        self.uri_updates = {}
        self.uris_by_recent_update = []
        self.limit = limit
        self.uri_references = {}

    def count_references(self, refs, uri):
        if self.uri_references.has_key(uri) == False:
            self.uri_references[uri] = defaultdict(int)
        for ref in refs:
            self.uri_references[uri][ref] += 1

    def contains_duplicate_references(self, uri):
        if self.uri_references.has_key(uri):
           refs = self.uri_references[uri].keys()
           for ref in refs:
                if self.uri_references[uri][ref] > 1:
                    return True
        return False

    def add_row(self, row):
        info = Hypothesis.get_info_from_row(row)
        uri = info['uri']
        refs = info['references']
        self.count_references(refs, uri)
        if self.contains_duplicate_references(uri):
            return
        else:
            references_html = Hypothesis.make_references_html(info)

        quote_html = Hypothesis.make_quote_html(info)
        text_html = Hypothesis.make_text_html(info)
        tag_html = Hypothesis.make_tag_html(info)
        doc_title = info['doc_title']
        updated = info['updated']
        is_page_note = info['is_page_note']
        if self.uri_updates.has_key(uri) == True:  # track most-recent update per uri
            if updated < self.uri_updates[uri]:
                self.uri_updates[uri] = updated
        else:
            self.uri_updates[uri] = updated
        references = info['references']
        self.uri_bundles[uri].append( {'uri':uri, 'doc_title':doc_title,'updated':updated, 
                                       'references_html':references_html, 'quote_html':quote_html, 
                                        'text_html':text_html, 'tag_html':tag_html, 
                                        'is_page_note':is_page_note, 'references':references} )

    def sort(self):
        sorted_uri_updates = sorted(self.uri_updates.items(), key=operator.itemgetter(1), reverse=True)
        for update in sorted_uri_updates:
            self.uris_by_recent_update.append( update[0] )


def make_user_activity(request, user):

    activity = HypothesisUserActivity(limit=15)
    response = requests.get('%s/search?user=%s&limit=200' %
                        (Hypothesis().api_url, user) )

    rows = response.json()['rows']
        
    for row in rows:
        activity.add_row(row)
    activity.sort()

    s = ''

    for uri in activity.uris_by_recent_update:

        bundles = activity.uri_bundles[uri]

        for i in range(len(bundles)):

            bundle = bundles[i]

            if i == 0:
                dt_str = bundle['updated']
                dt = datetime.strptime(dt_str[0:16], "%Y-%m-%dT%H:%M")
                when = Hypothesis.friendly_time(dt)
                doc_title = bundle['doc_title']
                via_url = Hypothesis().via_url
                s += '<div class="stream-url">'
                if uri.startswith('http'):
                  s += """<a target="_new" class="ng-binding" href="%s">%s</a> 
        (<a title="use Hypothesis proxy" target="_new" href="%s/%s">via</a>)"""  % (uri, doc_title, via_url, uri)
                else:
                  s += doc_title
                s += """<span class="annotation-timestamp small pull-right ng-binding ng-scope">{%s}</span>
        </div>""" % when

            references_html = bundle['references_html']
            quote_html = bundle['quote_html']
            text_html = bundle['text_html']
            tag_html = bundle['tag_html']

            is_page_note = bundle['is_page_note']

            if quote_html != '':
                s += """<div class="stream-quote">%s</div>"""  % quote_html

            if text_html != '' and references_html == '':
                s += """<div class="stream-text">%s</div>""" %  text_html

            if references_html != '':
                s += '<p class="stream-reference">%s</p>\n' % references_html

            if tag_html != '':
                s += '<div class="stream-tags">%s</div>' % tag_html

    return s

def format_active_users(user):
    active_users = Hypothesis().get_active_users()
    select = ''
    for active_user in active_users:
        if active_user[0] == user:
            option = '<option selected value="%s">%s (%s)</option>'
        else:
            option = '<option value="%s">%s (%s)</option>'
        option = option % (active_user[0], active_user[0], active_user[1])
        select += option
    select = """<select class="stream-active-users" name="active_users" 
onchange="javascript:show_user()">
%s
</select>""" % select
    return select

def user_activity(request,body):
    q = urlparse.parse_qs(request.query_string)
    if q.has_key('user'):
        user = q['user'][0]
    else:
        users = Hypothesis().get_active_users()
        user = users[0][0]
    users = format_active_users(user)    
    head = '<h1>Hypothesis activity for %s</h1>' % user
    body = make_user_activity(request,user)
    return renderers.render(
        'h:templates/stream.html', {'head':head, 'users':users, 'main':body}, request=request)