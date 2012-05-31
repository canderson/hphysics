import sys, re
from BeautifulSoup import BeautifulSoup as BS

sys.path.append('../bibtex/')

import www, pacs, bibtex
import hphys_types as ht

def author_search(first, middle, last):
    """Given a first, middle, and last name, returns a list of ADS codes (as strings) matching the query.
    Example inputs:
    first="M.", middle="D.", last="Lukin"
    first="Mikhail", middle="D.", last="Lukin"
    first="Mikhail", middle="Deluxe", last="Lukin"
    """
    out = []

    SEARCH_BASE = "http://adsabs.harvard.edu/cgi-bin/nph-abs_connect?return_req=no_params&author=%s, %s %s"
    #    FIRST_INDEX = 1
    #    MAX_WINDOW = 500
    url = SEARCH_BASE % (last, first, middle)
    while url:
        url = url.replace(" ","%20") # We do not normalize the URL because it changes ADS' behavior
        url = url.replace('&#38;','&amp;') # To get around ADS' URL parsing
        html = www.open_http(url, True)
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
    auths = map(lambda x: ht.Name({"names": x[1].split(' '), "last": x[0]}),auths)

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
    print dp
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
    ADS_ABS = "http://adsabs.harvard.edu/abs/%s" % bibcode
    ADS_TO_EPRINT = "http://adsabs.harvard.edu/cgi-bin/nph-data_query?bibcode=%s&link_type=EJOURNAL" % bibcode
    ADS_TO_ARXIV = "http://adsabs.harvard.edu/cgi-bin/nph-data_query?bibcode=%s&link_type=PREPRINT" % bibcode
    ADS_ABS_BIBTEX = "http://adsabs.harvard.edu/cgi-bin/nph-bib_query?bibcode=%s&data_type=BIBTEX" % bibcode

    ads_abs_s, _ = www.open_http(ADS_ABS)
    # ads_abs_soup = BS(ads_abs_s)

    # Get some BibTeX
    bibtex_records = bibtex.read_string(www.open_http(ADS_ABS_BIBTEX)[0])
    assert len(bibtex_records) == 1
    br = bibtex_records[0]
    out = ht.Publication()
    out.publication_type = br.entry_type
    out.ads_bibcode = bibcode
    out.title = ht.LatexString({"contents": br.get("title")})
    out.doi = br.get("doi")

    ## The "main" datetime. There's a risk for some error here, because ADS doesn't date its info. But we will assume that all of its info was correct at the date of publication given by the bibtex record.
    # Read date from HTML
    # nodes = ads_abs_soup.findAll(attrs={"name": "citation_date"})
    # m_y = map(int,nodes[0]['content'].split('/'))
    # main_date = ht.MonthYear({'month': m_y[0], 'year': m_y[1]})
    main_date = ht.MonthYear({'month': br.date[0], 'year': br.date[1]})
    ##

    authors = affiliations_from_abstract(ads_abs_s)
    # TODO cross-reference our existing databse of authors
    out.authors = None
                
    # Code to get authors from bibtex.
    #    authors = []
    #    for x in br.get('author'):
    #        a = Author()
    #        authors.append(a)
    #        a.name.update((main_date, x[0]))
    #        a.honorifics.update((main_date, x[1]))
    #    out.authors = authors

    pacs_set = set()
    keywords_set = set()

    pacs_line = r'<tr><td nowrap valign="top" align="left"><b>PACS Keywords:</b></td><td><br></td><td align="left" valign="top">(.*?)</td></tr>'
    m = re.search(pacs_line,ads_abs_s)
    if m:
        p, k = pacs_keywords_parse(m.group(1))
        pacs_set.update(p)
        keywords_set.update(k)

    # Start recording particular versions
    out.published_snapshots = []

    if br.get('journal'):
        # TODO These pages might need to set cookies or do other awful things:
        eprint_page, eprint_url = www.open_http(ADS_TO_EPRINT)
        # TODO Record these somewhere central so we can research what domains they're coming from.

        v = ht.JournalSnapshot()
        out.published_snapshots.append(v)
        v.date = main_date
        for x in v.bibtex_names():
            val = br.get(x)
            if val: setattr(v,x,val)
        v.url = eprint_url
        print v.url
        pacs_set.update(re.findall(pacs.PACS_REGEX, eprint_page))

    return out

    # TODO. The following is not completed yet.

    if br.get('archiveprefix') == "arXiv":
        arxiv_page, arxiv_url = www.open_http(ADS_TO_ARXIV)
        entry = ht.ArxivEntry()
        entry.arxiv_id = br.get('eprint')
        # TODO populate
        snapshots = []
        for x in arxiv_abs_versions(arxiv_page):
            v = ArxivSnapshot()
            #TODO populate
            snapshots.append(v)
        entry.snapshots = snapshots
    out.arxiv_entry = entry
