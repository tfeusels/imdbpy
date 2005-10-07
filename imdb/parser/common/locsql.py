"""
locsql module (imdb.parser.common package).

This package provides some modules containing code shared amongst
"local" and "sql" parsers.

Copyright 2005 Davide Alberani <da@erlug.linux.it> 

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
import re

from imdb import IMDbBase
from imdb.Person import Person
from imdb.Movie import Movie
from imdb._exceptions import IMDbDataAccessError
from imdb.utils import analyze_title, build_title, analyze_name, \
                        build_name, canonicalTitle, canonicalName, \
                        normalizeName, re_titleRef, re_nameRef, \
                        re_year_index, _articles

_ltype = type([])
_dtype = type({})
_stypes = (type(''), type(u''))

re_nameIndex = re.compile(r'\(([IVXLCDM]+)\)')


class IMDbLocalAndSqlAccessSystem(IMDbBase):
    """Base class for methods shared by the 'local' and the 'sql'
    data access systems."""

    def _searchIMDbMoP(self, params):
        """Fetch the given web page from the IMDb akas server."""
        import urllib
        from imdb.parser.http import IMDbURLopener
        params = urllib.urlencode(params)
        url = 'http://akas.imdb.com/find?%s' % params
        content = ''
        try:
            urlOpener = IMDbURLopener()
            uopener = urlOpener.open(url)
            content = uopener.read()
            uopener.close()
            urlOpener.close()
        except (IOError, IMDbDataAccessError):
            pass
        return content

    def _httpMovieID(self, titline):
        """Translate a movieID in an imdbID.
        Try an Exact Primary Title search on IMDb;
        return None if it's unable to get the imdbID.
        """
        if not titline: return None
        params = {'q': titline, 's': 'pt'}
        content = self._searchIMDbMoP(params)
        if not content: return None
        from imdb.parser.http.searchMovieParser import BasicMovieParser
        mparser = BasicMovieParser()
        result = mparser.parse(content)
        if not (result and result.get('data')): return None
        return result['data'][0][0]

    def _httpPersonID(self, name):
        """Translate a personID in an imdbID.
        Try an Exact Primary Name search on IMDb;
        return None if it's unable to get the imdbID.
        """
        if not name: return None
        params = {'q': name, 's': 'pn'}
        content = self._searchIMDbMoP(params)
        if not content: return None
        from imdb.parser.http.searchPersonParser import BasicPersonParser
        pparser = BasicPersonParser()
        result = pparser.parse(content)
        if not (result and result.get('data')): return None
        return result['data'][0][0]

    def _findRefs(self, o, trefs, nrefs):
        """Find titles or names references in strings."""
        to = type(o)
        if to in _stypes:
            for title in re_titleRef.findall(o):
                rtitle = build_title(analyze_title(title, canonical=1),
                                    canonical=1)
                if trefs.has_key(rtitle): continue
                movieID = self._getTitleID(rtitle)
                if movieID is None:
                    movieID = self._getTitleID(title)
                if movieID is None: continue
                m = Movie(movieID=movieID, title=rtitle,
                            accessSystem=self.accessSystem)
                trefs[rtitle] = m
            for name in re_nameRef.findall(o):
                rname = build_name(analyze_name(name, canonical=1),
                                    canonical=1)
                if nrefs.has_key(rname): continue
                personID = self._getNameID(rname)
                if personID is None:
                    personID = self._getNameID(name)
                if personID is None: continue
                p = Person(personID=personID, name=rname,
                            accessSystem=self.accessSystem)
                nrefs[rname] = p
        elif to is _ltype:
            for item in o:
                self._findRefs(item, trefs, nrefs)
        elif to is _dtype:
            for value in o.values():
                self._findRefs(value, trefs, nrefs)
        return (trefs, nrefs)

    def _extractRefs(self, o):
        """Scan for titles or names references in strings."""
        trefs = {}
        nrefs = {}
        return self._findRefs(o, trefs, nrefs)

    def _titleVariations(self, title):
        """Build title variations useful for searches."""
        title1 = title
        title2 = title3 = ''
        if re_year_index.search(title):
            # If it appears to have a (year[/imdbIndex]) indication,
            # assume that a long imdb canonical name was provided.
            titldict = analyze_title(title, canonical=1)
            # title1: the canonical name.
            title1 = titldict['title']
            # title3: the long imdb canonical name.
            title3 = build_title(titldict, canonical=1)
        else:
            # Just a title.
            # title1: the canonical title.
            title1 = canonicalTitle(title)
            title3 = ''
        # title2 is title1 without the article, or title1 unchanged.
        if title2 != title1: hasArt = 1
        title2 = title1
        t2s = title2.split(', ')
        if t2s[-1] in _articles:
            title2 = ', '.join(t2s[:-1])
        return title1, title2, title3

    def _nameVariations(self, name):
        """Build name variations useful for searches."""
        name1 = name
        name2 = name3 = ''
        if re_nameIndex.search(name):
            # We've a name with an (imdbIndex)
            namedict = analyze_name(name, canonical=1)
            # name1 is the name in the canonical format.
            name1 = namedict['name']
            # name3 is the canonical name with the imdbIndex.
            name3 = build_name(namedict, canonical=1)
        else:
            # name1 is the name in the canonical format.
            name1 = canonicalName(name)
            name3 = ''
        # name2 is the name in the normal format, if it differs from name1.
        name2 = normalizeName(name1)
        if name1 == name2: name2 = ''
        return name1, name2, name3
