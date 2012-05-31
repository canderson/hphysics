import www
import xml.dom.minidom as xdm
import datetime
# When you decide to solve a problem with regular expressions, you now have two problems.
import re

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

        pdf, _ = self.open_http("http://arxiv.org/pdf/%s" % self.id)
        pdf_file.write(pdf)
        pdf_file.close()

        out.append(["pdf",pdf_path])

        source, _, source_info = self.open_http("http://arxiv.org/e-print/%s" % self.id, True)
        encoding = source_info['content-encoding']
        if encoding == 'x-gzip':
            source_path = path + "%s-source.gz"
            source_file = open( source_path % self.id,'w')
            source_file.write(source)
            source_file.close()
            out.append(['gz',source_path])

        return out

    def abs_html(self):
        if not self._abs_html:
            abs_url = "http://arxiv.org/abs/%s" % self.id
            self._abs_html, _ = self.open_http(abs_url)
        return self._abs_html

    def entry_xml(self):
        if not self._entry_xml:
            atom_url = "http://export.arxiv.org/api/query?id_list=%s" % self.id
            s, _ = self.open_http(atom_url)
            self._entry_xml = xdm.parseString(s).getElementsByTagName("entry")[0]
        return self._entry_xml

    def open_http(self, url, verbose=False):
        res = www.open_http_raw(url)
        if verbose:
            return ''.join(res.readlines()), res.geturl(), res.info()
        else:
            return ''.join(res.readlines()), res.geturl()
        
        
    def set_recovery(self):
        """If you don't want to be responsible for HTTP errors, then set the object's recovery behavior."""
        pass

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
            p, _ = self.open_http(url)
            self._abs_html_old.append(p)
            m = re.search(r'<td class="tablecell comments">(.*?)</td>', p, flags = re.MULTILINE)
            if m: 
                self._comments.append(m.group(1))
            else: self._comments.append('')
        return self._comments
