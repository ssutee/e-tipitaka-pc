from cgi import escape as htmlescape

class MyHtmlFormatter(object):
    def __init__(self, tagname="strong", attrs="", between="...", classname="match", termclass="term"):
        self.between = between
        self.tagname = tagname
        self.classname = classname
        self.termclass = termclass
        self.attrs = attrs

    def _format_fragment(self, text, fragment, seen):
        tagname = self.tagname
        attrs = self.attrs
        htmlclass = " ".join((self.classname, self.termclass))

        output = []
        index = fragment.startchar

        for t in fragment.matches:
            if t.startchar > index:
                output.append(text[index:t.startchar])

            ttxt = htmlescape(text[t.startchar:t.endchar])
            if t.matched:
                if t.text in seen:
                    termnum = seen[t.text]
                else:
                    termnum = len(seen)
                    seen[t.text] = termnum
                ttxt = '<%s %s class="%s%s">%s</%s>' % (tagname, attrs, htmlclass, termnum, ttxt, tagname)

            output.append(ttxt)
            index = t.endchar

        return "".join(output)

    def __call__(self, text, fragments):
        seen = {}
        return self.between.join(self._format_fragment(text, fragment, seen) for fragment in fragments)
