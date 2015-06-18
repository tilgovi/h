import requests, json, types, re, operator, traceback
from pyramid.response import Response
from datetime import datetime
from collections import defaultdict
from markdown import markdown
import urlparse

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode


class HypothesisUtils:

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
        r = requests.get(self.app_url)
        cookies = r.cookies
        payload = {"username":self.username,"password":self.password}
        self.csrf_token = cookies['XSRF-TOKEN']
        data = json.dumps(payload)
        headers = {'content-type':'application/json;charset=UTF-8', 'x-csrf-token': self.csrf_token}
        r = requests.post(url=self.app_url  + "?__formid__=login", data=data, cookies=cookies, headers=headers)
        url = self.api_url + "/token?" + urlencode({'assertion':self.csrf_token})
        r = (requests.get(url=url,
                         cookies=cookies, headers=headers))
        self.token =  r.content

    def search_all(self):
        params = {'limit':200, 'offset':0 }
        while True:
            h_url = self.query_url.format(query=urlencode(params))
            r = requests.get(h_url).json()
            rows = r.get('rows')
            params['offset'] += len(rows)
            if len(rows) is 0:
                break
            for row in rows:
                yield row

    """ 
    "link": [
    {
        "href": "http://thedeadcanary.wordpress.com/2014/05/11/song-of-myself/"
    }, 
    {
        "href": "http://thedeadcanary.wordpress.com/2014/05/11/song-of-myself/", 
        "type": "", 
        "rel": "canonical"
    }, 
    """

    def make_annotation_payload(self, url, start_pos, end_pos, prefix, quote, suffix, text, tags, link):
        payload = {
            "uri": url,
            "user": 'acct:' + self.username + '@hypothes.is',
            "permissions": {
                "read": ["group:__world__"],
                "update": ['acct:' + self.username + '@hypothes.is'],
                "delete": ['acct:' + self.username + '@hypothes.is'],
                "admin":  ['acct:' + self.username + '@hypothes.is']
                },
            "document": {
                "link":  link   # link is a list of dict
                },
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
        return payload

    def create_annotation(self, url=None, start_pos=None, end_pos=None, prefix=None, 
               quote=None, suffix=None, text=None, tags=None, link=None):
        headers = {'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json;charset=utf-8' }
        payload = self.make_annotation_payload(url, start_pos, end_pos, prefix, quote, suffix, text, tags, link)
        data = json.dumps(payload, ensure_ascii=False)
        r = requests.post(self.api_url + '/annotations', headers=headers, data=data)
        return r

    def call_search_api(self, args={'limit':200}):
        h_url = self.query_url.format(query=urlencode(args))
        json = requests.get(h_url).json()
        return json

    def get_active_users(self):
        j = self.call_search_api()
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

        if r.has_key('document') and r['document'].has_key('link'):
            links = r['document']['link']
            if type(links) != type(list()):
                links = [{'href':links}]
        else:
            links = []

        return {'updated':updated, 'user':user, 'uri':uri, 'doc_title':doc_title, 
                'tags':tags, 'text':text, 'references':refs, 'target':target, 'is_page_note':is_page_note, 'links':links }

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
        quote = ''
        try:
          if info.has_key('target') == False:
              return quote 
          target = info['target']
          if isinstance(target,list) and len(target) == 0:
              return quote
          dict = {}
          if isinstance(target,list) and len(target) > 0:
              dict = target[0]
          else:
              dict = target
          if dict.has_key('selector') == False:
              return quote 
          uri = info['uri']
          selector = dict['selector']
          for sel in selector:
              if sel.has_key('exact'):
                  quote = sel['exact']
        except:
          s = traceback.format_exc()
          print s
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
        anno_url = HypothesisUtils().anno_url
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

    @staticmethod
    def alt_stream_js(request):
        from pyramid.response import Response
        js = """
    function embed_conversation(id) {
        element = document.getElementById(id);
        element.outerHTML = '<iframe height="300" width="85%" src="https://hypothes.is/a/' + id + '"/>'
        return false;
    }

    function show_user() {
       var select = document.getElementsByName('active_users')[0];
       var i = select.selectedIndex;
       var user = select[i].value;
       location.href= '/stream.alt?user=' + user;
    } """
        r = Response(js)
        r.content_type = b'text/javascript'
        return r

class HypothesisStream:

    def __init__(self):
        self.uri_bundles = defaultdict(list)
        self.uri_updates = {}
        self.uris_by_recent_update = []
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
        info = HypothesisUtils.get_info_from_row(row)
        user = info['user']
        uri = info['uri']
        refs = info['references']
        self.count_references(refs, uri)
        if self.contains_duplicate_references(uri):
            return
        else:
            references_html = HypothesisUtils.make_references_html(info)

        quote_html = HypothesisUtils.make_quote_html(info)
        text_html = HypothesisUtils.make_text_html(info)
        tag_html = HypothesisUtils.make_tag_html(info)
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
                                        'text_html':text_html, 'tag_html':tag_html, 'user':user,
                                        'is_page_note':is_page_note, 'references':references} )

    def sort(self):
        sorted_uri_updates = sorted(self.uri_updates.items(), key=operator.itemgetter(1), reverse=True)
        for update in sorted_uri_updates:
            self.uris_by_recent_update.append( update[0] )

    @staticmethod
    def get_most_active_user_and_picklist_and_list(q):
        if q.has_key('user'):
            user = q['user'][0]
            user, picklist, list = HypothesisStream.format_active_users(user=user)
        else:
            user, picklist, list = HypothesisStream.format_active_users(user=None)
        list = [x[0] for x in list]
        return user, picklist, list

    @staticmethod
    def alt_stream(request):
        q = urlparse.parse_qs(request.query_string)
        user, picklist, list = HypothesisStream.get_most_active_user_and_picklist_and_list(q)  
        if q.has_key('user'):
            user = q['user'][0]
            if user not in list:
                picklist = ''
        if q.has_key('by_url'):
            head = '<p class="stream-selector"><a href="/stream.alt">view recently active users</a></p>'
            head += '<h1>urls recently annotated</h1>'
            body = HypothesisStream.make_alt_stream(by_url=True)
        else:
            head = '<p class="stream-selector"><a href="/stream.alt?by_url=yes">view recently annotated urls</a></p>'
            head += '<h1 class="stream-active-users-widget">urls recently annotated by {user} <span class="stream-picklist">{users}</span></h1>'.format(user=user, users=picklist)
            body = HypothesisStream.make_alt_stream(user=user)
        html = HypothesisStream.alt_stream_template( {'head':head,  'main':body} )
        return Response(html.encode('utf-8'))

    @staticmethod
    def make_alt_stream(user=None, by_url=False):
        activity = HypothesisStream()
        if user is not None:
            response = requests.get('%s/search?user=%s&limit=200' %
                            (HypothesisUtils().api_url, user) )
        elif by_url == True:
            response = requests.get('%s/search?limit=200' % HypothesisUtils().api_url)
        else:
            return Response('what now?')

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
                    when = HypothesisUtils.friendly_time(dt)
                    doc_title = bundle['doc_title']
                    via_url = HypothesisUtils().via_url
                    s += '<div class="stream-url">'
                    if uri.startswith('http'):
                      s += """<a target="_new" class="ng-binding" href="%s">%s</a> 
            (<a title="use Hypothesis proxy" target="_new" href="%s/%s">via</a>)"""  % (uri, doc_title, via_url, uri)
                    else:
                      s += doc_title
                    s += """<span class="annotation-timestamp small pull-right ng-binding ng-scope">%s</span>
            </div>""" % when

                s += '<div class="paper stream-quote">'

                if by_url == True:
                    user = bundle['user']
                    s += '<p class="stream-user">%s</p>' % user

                references_html = bundle['references_html']
                quote_html = bundle['quote_html']
                text_html = bundle['text_html']
                tag_html = bundle['tag_html']

                is_page_note = bundle['is_page_note']

                if quote_html != '':
                    s += """<p class="annotation-quote">%s</p>"""  % quote_html

                if text_html != '' and references_html == '':
                    s += """<p class="stream-text">%s</p>""" %  (text_html)

                if references_html != '':
                    s += '<p class="stream-reference">%s</p>\n' % references_html

                if tag_html != '':
                    s += '<p class="stream-tags">%s</p>' % tag_html

                s += '</div>'

        return s

    @staticmethod        
    def format_active_users(user=None):
        active_users = HypothesisUtils().get_active_users()
        most_active_user = active_users[0][0]
        select = ''
        for active_user in active_users:
            if user is not None and active_user[0] == user:
                option = '<option selected value="%s">%s (%s)</option>'
            else:
                option = '<option value="%s">%s (%s)</option>'
            option = option % (active_user[0], active_user[0], active_user[1])
            select += option
        select = """<select class="stream-active-users" name="active_users" 
    onchange="javascript:show_user()">
    %s
    </select>""" % select
        return most_active_user, select, active_users

    @staticmethod
    def alt_stream_template(args):
        return u"""<html>
<head>
    <link rel="stylesheet" href="https://hypothes.is/assets/styles/app.min.css" /> 
    <link rel="stylesheet" href="https://hypothes.is/assets/styles/hypothesis.min.css" />
    <style>
    body {{ padding: 10px; font-size: 10pt; position:relative}}
    h1 {{ font-weight: bold; margin-bottom:10pt }}
    .stream-url {{ margin-top: 12pt; margin-bottom: 4pt; overflow:hidde; border-style: solid; border-color: rgb(179, 173, 173); border-width: thin; padding: 4px;}}
    .stream-reference {{ margin-bottom:10pt; /*margin-left:6%*/ }}
    .stream-quote {{ /*margin-left: 3%;*/ margin-bottom: 4pt; font-style: italic }}
    .stream-text {{ margin-bottom: 4pt; /*margin-left:7%;*/ word-wrap: break-word }}
    .stream-tags {{ margin-bottom: 10pt; }}
    .stream-user {{ font-weight: bold; margin-bottom: 4pt}}
    .stream-selector {{ float:right; }}
    .stream-picklist {{ margin-left: 20pt }}
    .stream-active-users-widget {{ margin-top:0;}}
    ul, li {{ display: inline }}
    li {{ color: #969696; font-size: smaller; border: 1px solid #d3d3d3; border-radius: 2px; padding: 0 .4545em .1818em }}
    img {{ max-width: 100% }}
    annotation-timestamp {{ margin-right: 20px }}
    img {{ padding:10px }}
    a {{ word-wrap: break-word }}
    </style>
</head>
<body class="ng-scope">
{head}
{main}
<script src="/stream.alt.js"></script>
</body>
</html> """.format(head=args['head'],main=args['main'])

"""
if __name__ == '__main__':
    h = HypothesisUtils('judell','hy$qvr')
    h.login()
    assert (unicode('??','utf-8').encode('utf-8') == '??')
    #u1 = unicode(s,'utf-8').encode('utf-8')
    u = '\xe0\xae\xae\xe0\xaf\x8a'
    h.create_annotation("http://jonudell.net/", 0, 0, None, None, None, u, [], [])
    pass
"""
