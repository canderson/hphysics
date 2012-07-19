import sys, re, os
from BeautifulSoup import BeautifulSoup as BS
from time import time, sleep

sys.path.append('../bibtex/')

import www, pacs, bibtex, arxiv
import hphys_types as ht

class HTTP_Opener():
    def __init__(self):
        self.prev_time = None
        self.WAIT_TIME = 10 # Minimum wait, in seconds, between loading two ADS resources.
    def open(self,url):
        """Handles all errors by waiting ten seconds and trying again."""
        while True:
            my_time = time()
            if self.prev_time:
                # If something messes with the system clock, this assert might fire:
                assert(my_time > self.prev_time)
                sleep(self.WAIT_TIME - min((my_time - self.prev_time), self.WAIT_TIME))
            self.prev_time = my_time
            try: 
                out = www.open_http(url)
                return out
            except:
                print "HTTP failed"
                sleep(10)

http_opener = HTTP_Opener()

def author_search(first, middle, last):
    """Given a first, middle, and last name, returns a list of ADS codes (as strings) matching the query.
    Example inputs:
    first="M.", middle="D.", last="Lukin"
    first="Mikhail", middle="D.", last="Lukin"
    first="Mikhail", middle="Deluxe", last="Lukin"
    """
    out = []

    search_str = "%s, %s" % (last, first)
    if middle:
        search_str = search_str + " " + middle

    # Search engine details:
    ## Last name must match exactly
    ## For first name: checks if either string is a prefix of the other.
    SEARCH_BASE = "http://adsabs.harvard.edu/cgi-bin/nph-abs_connect?return_req=no_params&author=%s"


    #    FIRST_INDEX = 1
    #    MAX_WINDOW = 500
    url = SEARCH_BASE % search_str
    while url:
        url = url.replace(" ","%20") # We do not normalize the URL because it changes ADS' behavior
        url = url.replace('&#38;','&amp;') # To get around ADS' URL parsing
        # open_http returns html-content, url
        html = http_opener.open(url)[0]
        soup = BS(html)
        nodes = soup.findAll(attrs={"type": "checkbox", "name": "bibcode"})
        out.extend(map(lambda x: x["value"], nodes))
        # Get <a href="http://adsabs.harvard.edu/cgi-bin/nph-abs_connect?return_req=no_params&amp;author=Lukin,%20M.%20D.&amp;start_nr=251&amp;start_cnt=201">next set of references</a>
        match = re.search(r'Get <a href="(.*?)">next set of references</a>',html)
        if match:
            url = match.group(1)
        else:
            url = None
    return out

def affiliations_from_abstract(s):
    """Takes the text of the abstract page and returns a list of tuples of the form (Name of author, String representing affiliation)."""
    auth_line_start = r'<tr><td nowrap valign="top" align="left"><b>Authors:</b></td><td><br></td><td align="left" valign="top">'
    auth_line_end = r'</td></tr>'

    aff_line_start = r'<tr><td nowrap valign="top" align="left"><b>Affiliation:</b></td><td><br></td><td align="left" valign="top">'
    aff_line_end = r'</td></tr>'

    auth_pattern = r'<a href=".*?">(.*?)</a>'
    aff_pattern = r'([A-Z][A-Z][A-Z]?[A-Z]?)\((.*?)\)'

    # re.MULTILINE means that ^ and $ match the beginning and end of a line
    auth_line = re.search('^' + auth_line_start + r'(.*?)' + auth_line_end, s, flags=re.MULTILINE)

    auths = [x for x in re.findall(auth_pattern, auth_line.group(0))]
    # Each element of auths has the form "Kozlenko,&#160;D.&#160;P."
    auths = map(lambda x: x.replace("&#160;"," ").split(", "), auths)
    try:
        names = x[1].split(' ')
    except IndexError:
        names = []
    auths = map(lambda x: ht.Name({"names": names, "last": x[0]}),auths)

    aff_line = re.search('^' + aff_line_start + r'(.*?)' + aff_line_end, s, flags=re.MULTILINE)
    if aff_line:
        # The output of findall is a list of tuples iff there is more than one group in the pattern.
        affs = [x[1] for x in re.findall(aff_pattern, aff_line.group(0))]
    else: affs = [None] * len(auths)

    return zip(auths,affs)

def pacs_keywords_parse(s):
    """ADS has a 'PACS Keywords' field that consists of a bunch of PACS names delimited by ', '. Of course, PACS names can include ', ' so this is a mess. This function returns a tuple of lists. The first list is the valid PACS codes that we could extract from the string. The second list is phrases that we ignored. This function tries to ignore as few phrases as possible."""
    units = s.split(', ')
    unitsl = len(units)
    #[Prev, Word, Valid, Cost]
    dp = [[None, None, None, 0]]
    for cur in range(1, len(units) + 1):
        dp.append([None, None, None, unitsl + 1])
        for i in range(1, cur + 1):
            phrase = ", ".join(units[cur - i:cur])
            candidate = pacs.PACS_NAMES.get(phrase)
            if candidate:
                working = [cur - i, candidate, True, dp[cur - i][-1]]
            else:
                working = [cur - i, phrase, False, dp[cur - i][-1] + 1]
            if working[-1] < dp[-1][-1]:
                dp[-1] = working
    codes_out = []
    phrases_out = []
    i = unitsl
    if dp[i]:
        while True:
            if dp[i][2]:
                codes_out.append(dp[i][1])
            else:
                phrases_out.append(dp[i][1])
            i = dp[i][0]
            if i == 0: break
    return (codes_out,phrases_out)
    
def abstract_read(bibcode):
    TRY_EPRINT_URLS = False 
    TRY_ARXIV = False

    ADS_ABS = "http://adsabs.harvard.edu/abs/%s" % bibcode
    ADS_TO_EPRINT = "http://adsabs.harvard.edu/cgi-bin/nph-data_query?bibcode=%s&link_type=EJOURNAL" % bibcode
    ADS_TO_ARXIV = "http://adsabs.harvard.edu/cgi-bin/nph-data_query?bibcode=%s&link_type=PREPRINT" % bibcode
    ADS_ABS_BIBTEX = "http://adsabs.harvard.edu/cgi-bin/nph-bib_query?bibcode=%s&data_type=BIBTEX" % bibcode

    out = ht.Publication()
    out.ads_bibcode = bibcode

    ads_abs_s, _ = http_opener.open(ADS_ABS)
    # ads_abs_soup = BS(ads_abs_s)

    authors = affiliations_from_abstract(ads_abs_s)
    # TODO cross-reference our existing databse of authors
    out.authors = map(lambda x: {"name": x[0], "affiliation": x[1]}, authors)

    # Get the text of the abstract
    abs_start = r'<h3 align="center">                               Abstract</h3>\n'
    m = re.search(abs_start + r'((.*?\n)*?)<hr>',ads_abs_s)
    if m:
        out.abstract = ht.HTMLString({"contents": m.group(1)})

    # Get PACS codes and keywords
    pacs_set = set()
    keywords_set = set()

    pacs_line = r'<tr><td nowrap valign="top" align="left"><b>PACS Keywords:</b></td><td><br></td><td align="left" valign="top">(.*?)</td></tr>'
    m = re.search(pacs_line,ads_abs_s)
    if m:
        p, k = pacs_keywords_parse(m.group(1))
        pacs_set.update(p)
        keywords_set.update(k)

    # Get some BibTeX
    bibtex_records = bibtex.read_string(http_opener.open(ADS_ABS_BIBTEX)[0])
    assert len(bibtex_records) == 1
    br = bibtex_records[0]
    out.publication_type = br.entry_type
    out.title = ht.LatexString({"contents": br.get("title")})
    out.doi = br.get("doi")

    ## The "main" datetime. There's a risk for some error here, because ADS doesn't date its info. But we will assume that all of its info was correct at the date of publication given by the bibtex record.
    # Read date from HTML
    # nodes = ads_abs_soup.findAll(attrs={"name": "citation_date"})
    # m_y = map(int,nodes[0]['content'].split('/'))
    # main_date = ht.MonthYear({'month': m_y[0], 'year': m_y[1]})
    main_date = ht.MonthYear({'month': br.date[0], 'year': br.date[1]})
    ##

                
    # Code to get authors from bibtex.
    #    authors = []
    #    for x in br.get('author'):
    #        a = Author()
    #        authors.append(a)
    #        a.name.update((main_date, x[0]))
    #        a.honorifics.update((main_date, x[1]))
    #    out.authors = authors

    # Start recording particular versions
    out.published_snapshots = []

    if br.get('journal'):
        if TRY_EPRINT_URLS:
            # TODO These pages might need to set cookies or do other awful things:
            eprint_page, eprint_url = http_opener.open(ADS_TO_EPRINT)
            v.url = eprint_url
            pacs_set.update(re.findall(pacs.PACS_REGEX, eprint_page))
            # TODO Record these somewhere central so we can research what domains they're coming from.

        v = ht.JournalSnapshot()
        out.published_snapshots.append(v)
        v.date = main_date
        for x in v.bibtex_names():
            val = br.get(x)
            if val: setattr(v,x,val)

    if br.get('archiveprefix') == "arXiv" and TRY_ARXIV:
        arxiv_id = br.get('eprint')
        ar = arxiv.ArXivRecord(arxiv_id)
        entry = ht.ArxivEntry({'arxiv_id': arxiv_id})
        snapshots = []
        for i in range(0,len(ar.versions())):
            snapshots.append(ht.ArxivSnapshot({'date': ar.versions()[i], 'comment': ar.comments()[i], 'version': i + 1}))
        snapshots[-1].versions = ar.download(os.path.abspath("../files"))
        entry.snapshots = snapshots
        submitter = ar.submitter()
        if submitter:
            names = submitter.split(' ')
            entry.submitter = ht.Name({'names': names[:-1], 'last': names[-1]})
        c1, c_all = ar.categories()
        if c1:
            ar.primary_category = c1
            ar.categories = c_all
        out.arxiv_entry = entry

    # Now that we've looked-up online versions, we have all the PACS and keywords that we're going to get
    out.pacs_codes = list(pacs_set)
    out.keywords = list(keywords_set)
        
    return out
