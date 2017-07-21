# We need this in order to reduce the number of third-party modules.
# It is a part of code from http.client, that adjusted to work with
# asyncio in our specific case.

import email.message


class HTTPMessage(email.message.Message):
    def getallmatchingheaders(self, name):
        name = name.lower() + ':'
        n = len(name)
        lst = []
        hit = 0
        for line in self.keys():
            if line[:n].lower() == name:
                hit = 1
            elif not line[:1].isspace():
                hit = 0
            if hit:
                lst.append(line)
        return lst

async def parse_headers(fp, _class=HTTPMessage):
    headers = []
    while True:
        line = await fp.readline()
        headers.append(line)
        if line in (b'\r\n', b'\n', b''):
            break
    hstring = b''.join(headers).decode('iso-8859-1')
    return email.parser.Parser(_class=_class).parsestr(hstring)
