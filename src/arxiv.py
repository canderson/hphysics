import www
import xml.dom.minidom as xdm
import datetime
from time import time, sleep
# When you decide to solve a problem with regular expressions, you now have two problems.
import re

class HTTP_Opener():
    def __init__(self):
        self.prev_time = None
        self.WAIT_TIME = 60 # Minimum wait, in seconds, between loading two resources.
        self.user_agent = r'GilesBot/1.0 (downloading data for a short list of articles)'
    def open(self,url,verbose=False):
        """Handles all errors by crashing out."""
        while True:
            my_time = time()
            if self.prev_time:
                # If something messes with the system clock, this assert might fire:
                assert(my_time > self.prev_time)
                sleep(self.WAIT_TIME - min((my_time - self.prev_time), self.WAIT_TIME))
            self.prev_time = my_time
            try: 
                res = www.open_http(url,self.user_agent,True)
                if verbose:
                    return ''.join(res.readlines()), res.geturl(), res.info()
                else:
                    return ''.join(res.readlines()), res.geturl()
            except:
                print "HTTP failed"
                print url
                raise

http_opener = HTTP_Opener()

class ArXivRecord():
    def __init__(self, aid):
        self.id = aid
        self._abs_html = False # The HTML of the latest abstract page.
        self._abs_html_old = False # A list of the HTML of the old abstract pages.
        self._entry_xml = False
        self._categories = False
        self._versions = False
        self._submitter = False
        self._comments = False
        
    def download(self, path):

        path += '/'

        out = []

        pdf_path = path + "%s.pdf" % self.id
        # We let IOErrors bubble up
        pdf_file = open(pdf_path,'w')

        pdf, _ = http_opener.open("http://arxiv.org/pdf/%s" % self.id)
        pdf_file.write(pdf)
        pdf_file.close()

        out.append(["pdf",pdf_path])

        if "PDF only" in self.abs_html():
            print "No sources available."
            return out

        source, _, source_info = http_opener.open("http://arxiv.org/e-print/%s" % self.id, True)
        try:
            encoding = source_info['content-encoding']
        except KeyError:
            encoding = None
            print "Warning: could not get source file encoding :: %s." % self.id
            return out

        if encoding == 'x-gzip':
            source_path = path + "%s-source.gz"
            source_file = open( source_path % self.id,'w')
            source_file.write(source)
            source_file.close()
            out.append(['gz',source_path])
        else:
            print "Warning: Got a source file that was not a gzip :: %s." % self.id

        return out

    def abs_html(self):
        if not self._abs_html:
            abs_url = "http://arxiv.org/abs/%s" % self.id
            self._abs_html, _ = http_opener.open(abs_url)
        return self._abs_html

    def entry_xml(self):
        if not self._entry_xml:
            atom_url = "http://export.arxiv.org/api/query?id_list=%s" % self.id
            s, _ = http_opener.open(atom_url)
            self._entry_xml = xdm.parseString(s).getElementsByTagName("entry")[0]
        return self._entry_xml

    def preload(self, abs_html = True, entry_xml = True):
        """Normally, remote pages are lazily loaded. However, this means that any method that collects data could raise an error (because it went to lazily load a page and failed). If you don't want to be responsible for this, then use this method to preload everything you need. Once this is done, only self.download and self.comments can still raise an HTTP error."""
        if abs_html: self.abs_html()
        if entry_xml: self.entry_xml()

    def categories(self):
        """Returns a two-element list: [PrimaryCategory, [OtherCategory1, OtherCategory2, ...]]"""
        if self._categories:
            return self._categories
        exml = self.entry_xml()
        primary = exml.getElementsByTagName("arxiv:primary_category")[0].getAttribute("term")
        out = []
        self._categories = [primary, [x for x in map(lambda x: x.getAttribute("term"), exml.getElementsByTagName("category")) if x != primary]]
        return self._categories

    def submitter(self):
        """Returns a string giving the name of the submitter."""
        if self._submitter:
            return self._submitter
        m = re.search(r'<h2>Submission history</h2>\nFrom: (.*?) \[',self.abs_html())
        if m:
            self._submitter = m.group(1)
        return self._submitter

    def versions(self):
        """Returns a list of submission dateimes ordered by version number (1 .. n)."""
        if self._versions:
            return self._versions
        m = re.findall(r'^<b>(<a href="(.*?)">)?\[v([0-9]*?)\](</a>)?</b> (.*?)  \((.*?)\)<br />$', self.abs_html(), flags=re.MULTILINE)
        if m:
            out = [[int(x[2]), datetime.datetime.strptime(x[4],"%a, %d %b %Y %H:%M:%S %Z")] for x in m]
            self._versions = [x[1] for x in sorted(out, key=lambda x: x[0])]
        return self._versions

    def comments(self):
        """Returns a list of comments ordered by version number."""
        if self._comments: return self._comments
        numv = len(self.versions())
        self._abs_html_old = []
        self._comments = []
        for i in range(1, numv + 1):
            url = "http://arxiv.org/abs/%sv%d" % (self.id, i)
            p, _ = http_opener.open(url)
            self._abs_html_old.append(p)
            m = re.search(r'<td class="tablecell comments">(.*?)</td>', p, flags = re.MULTILINE)
            if m: 
                self._comments.append(m.group(1))
            else: self._comments.append('')
        return self._comments
