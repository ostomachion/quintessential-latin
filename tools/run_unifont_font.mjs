import {existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root=fileURLToPath(new URL('../',import.meta.url));
const local=path.join(root,'.venv-unifont',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const python=process.env.QLAT_UNIFONT_PYTHON||(existsSync(local)?local:'python');
const [action,...args]=process.argv.slice(2);
const script={build:'build_unifont_font.py',test:'test_unifont_font.py'}[action];
if(!script)throw new Error('Expected build or test');
const result=spawnSync(python,['-X','utf8',path.join(root,'tools',script),...args],{cwd:root,stdio:'inherit',windowsHide:true});
if(result.error)throw result.error;
process.exit(result.status??1);
