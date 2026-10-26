"""Serve the compiled Vue app locally; development builds remain separate."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path


class FrontendHandler(SimpleHTTPRequestHandler):
    extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.js':'application/javascript','.mjs':'application/javascript','.css':'text/css','.json':'application/json','.wasm':'application/wasm'}
    def do_GET(self):
        if self.path.split('?',1)[0]=='/__app_health__':
            payload=json.dumps({'app':'odm-tracker-frontend','build':self.server.build}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
        else:super().do_GET()
    def end_headers(self):
        self.send_header('Cache-Control','public, max-age=31536000, immutable' if self.path.startswith('/assets/') else 'no-store')
        self.send_header('X-Content-Type-Options','nosniff');super().end_headers()
    def log_message(self,format,*args):pass


def make_server(directory,port=5173):
    directory=Path(directory).resolve()
    if not (directory/'index.html').is_file():raise RuntimeError('网页构建入口不存在')
    server=ThreadingHTTPServer(('127.0.0.1',port),partial(FrontendHandler,directory=str(directory)))
    server.build=directory.name;return server


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);parser.add_argument('--port',type=int,default=5173)
    options=parser.parse_args()
    with make_server(options.directory,options.port) as server:server.serve_forever(poll_interval=.25)
