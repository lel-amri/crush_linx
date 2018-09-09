import z_base32
import urllib.parse
import werkzeug.routing as werkrout
import werkzeug.wrappers as werkwrap
import werkzeug.exceptions as werkexce
import werkzeug.utils as werkutil


class MemoryStorage(object):
    def __init__(self):
        self._urls_map = {}
        self._urls_id_map = {}
        self._id = 0

    @staticmethod
    def _compute_url_hash(url):
        return hash(url)

    def get_url(self, url_id):
        return self._urls_map.get(url_id)

    def store(self, url_id, url):
        if self.get_url_id(url) is not None:
            raise ValueError('The url already exists')
        self._urls_map[url_id] = url
        self._urls_id_map[self._compute_url_hash(url)] = url_id

    def get_url_id(self, url):
        h = self._compute_url_hash(url)
        return self._urls_id_map.get(h)

    @property
    def next_id(self):
        return self._id + 1

    def increment_id(self):
        self._id += 1


class CrushLinx(object):
    def __init__(self, storage=None):
        if storage is None:
            self._storage = Storage()
        else:
            self._storage = storage
        self._urls_map = werkrout.Map([
            werkrout.Rule('/', endpoint='new', methods=['GET', 'POST']),
            werkrout.Rule('/<url_id>', endpoint='redirect', methods=['GET'])
        ])

    @staticmethod
    def _url_is_valid(url):
        parts = urllib.parse.urlparse(url)
        if parts.scheme not in ('http', 'https'):
            return False
        return True

    def on_new(self, request):
        if 'url' in request.values:
            url = request.values['url']
            if not self._url_is_valid(url):
                return werkwrap.Response('Not ok')
            url_id = self._storage.get_url_id(url)
            if url_id is None:
                id_ = self._storage.next_id
                url_id = z_base32.encode_int(id_)
                self._storage.increment_id()
                self._storage.store(url_id, url)
            return werkwrap.Response(url_id)
        return werkwrap.Response('New ?')

    def on_redirect(self, request, url_id=None):
        url = self._storage.get_url(url_id)
        if url is None:
            raise werkexce.NotFound()
        return werkutil.redirect(url)

    @werkwrap.Request.application
    def __call__(self, request):
        urls = self._urls_map.bind_to_environ(request.environ)
        endpoint, arguments = urls.match()
        return getattr(self, 'on_' + endpoint)(request, **arguments)


if __name__ == '__main__':
    import werkzeug.serving as werkserv
    app = CrushLinx()
    werkserv.run_simple('127.0.0.1', 5000, app,\
            use_debugger=True, use_reloader=True)
