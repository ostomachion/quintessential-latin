import http from 'node:http';
import {readFile,stat} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../dist');
const args=process.argv.slice(2),port=Number(args[args.indexOf('--port')+1])||8767;
const mime={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.txt':'text/plain; charset=utf-8','.svg':'image/svg+xml','.pdf':'application/pdf','.ttf':'font/ttf','.otf':'font/otf','.woff2':'font/woff2'};
const server=http.createServer(async(request,response)=>{try{let pathname=decodeURIComponent(new URL(request.url,'http://localhost').pathname);if(pathname==='/quintessential-latin'){response.writeHead(301,{Location:'/quintessential-latin/'});response.end();return;}if(pathname.startsWith('/quintessential-latin/'))pathname=pathname.slice('/quintessential-latin'.length);let resolved=path.resolve(root,'.'+pathname);if(resolved!==root&&!resolved.startsWith(root+path.sep)){response.writeHead(403);response.end('Forbidden');return;}if((await stat(resolved)).isDirectory())resolved=path.join(resolved,'index.html');const data=await readFile(resolved);response.writeHead(200,{'Content-Type':mime[path.extname(resolved)]||'application/octet-stream','Cache-Control':'no-store'});response.end(request.method==='HEAD'?undefined:data);}catch{response.writeHead(404,{'Content-Type':'text/plain; charset=utf-8'});response.end('Not found');}});
server.listen(port,'127.0.0.1',()=>console.log(`Quintessential Latin: http://127.0.0.1:${port}/quintessential-latin/`));
