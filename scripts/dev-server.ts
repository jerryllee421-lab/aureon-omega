import { createServer } from 'node:http';
import api from '../api/[...path].ts';
createServer((req,res)=>{void api(req,res);}).listen(3001,'127.0.0.1',()=>console.log('AUREON API listening on http://127.0.0.1:3001'));
