# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import re
import htmlentitydefs

html_mark = re.compile(r"""(?P<html>(</|<!|<|&lt;)[-="' ;/.#:@\w]*(>|/>|&gt;))""")

def get_unicode_decoded_str(str, encodings): #TODO: rename 'str'
    for encoding in encodings:
        try:
            return unicode(str, encoding) if not isinstance(str, unicode) else str
        except:
            continue

    return u"".join([i if ord(i) < 128 else '?' for i in str]) #TODO: use genexpr

def strip_html_(html_content):
    is_html = True
    while is_html:
        reg = re.search(html_mark, html_content)
        if reg:
            html_content = html_content.replace(reg.groupdict().get('html'), '')
        else:
            is_html = False

    return html_content

def unescape(text):
   """Removes HTML or XML character references
      and entities from a text string.
      keep &amp;, &gt;, &lt; in the source code.
   from Fredrik Lundh
   http://effbot.org/zone/re-sub.htm#unescape-html
   """
   def fixup(m):
      text = m.group(0)
      if text[:2] == "&#":
         # character reference
         try:
            if text[:3] == "&#x":
               return unichr(int(text[3:-1], 16))
            else:
               return unichr(int(text[2:-1]))
         except ValueError:
#            print "erreur de valeur"
            pass
      else:
         # named entity
         try: #TODO: var = text[1:-1]
            if text[1:-1] == "amp":
               text = "&amp;amp;"
            elif text[1:-1] == "gt":
               text = "&amp;gt;"
            elif text[1:-1] == "lt":
               text = "&amp;lt;"
            else:
               text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
         except KeyError:
#            print "keyerror"
            pass
      return text # leave as is
   return re.sub("&#?\w+;", fixup, text)

def strip_html(text):
    """
    http://effbot.org/zone/re-sub.htm#strip-html
    """
    def fixup(m):
        text = m.group(0)
        if text[:1] == "<":
            return "" # ignore tags
        if text[:2] == "&#":
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        elif text[:1] == "&":
#            import htmlentitydefs
            entity = htmlentitydefs.entitydefs.get(text[1:-1])
            if entity:
                if entity[:2] == "&#":
                    try:
                        return unichr(int(entity[2:-1]))
                    except ValueError:
                        pass
                else:
                    return unicode(entity, "iso-8859-1")
        return text # leave as is
    return re.sub("(?s)<[^>]*>|&#?\w+;", fixup, text)
