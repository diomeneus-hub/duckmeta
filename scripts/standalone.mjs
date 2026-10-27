import { readFile, writeFile, readdir } from 'node:fs/promises';
// The production bundle has no runtime JS dependencies. Inline its static assets
// for a double-clickable, offline workshop without changing the development app.
const names=await readdir('dist/assets');
const css=await readFile(`dist/assets/${names.find(n=>n.endsWith('.css'))}`,'utf8');
let js=await readFile(`dist/assets/${names.find(n=>n.endsWith('.js'))}`,'utf8');
let html=await readFile('dist/index.html','utf8');
for(const name of ['duck.png','wizard.png']) {
 const data='data:image/png;base64,'+(await readFile(`public/assets/${name}`)).toString('base64');
 js=js.replaceAll(`/assets/${name}`,data);html=html.replaceAll(`/assets/${name}`,data);
}
js=js.replaceAll('/metapixels-reference.txt','data:text/plain;base64,'+(await readFile('public/metapixels-reference.txt')).toString('base64'));
html=html.replace(/<script type="module"[^>]*src="[^"]*"[^>]*><\/script>/,'').replace(/<link rel="stylesheet"[^>]*>/,'');
html=html.replace('</head>',()=>`<style>${css}</style></head>`);
html=html.replace('</body>',()=>`<script type="module">${js.replaceAll('</script','<\\/script')}</script></body>`);
await writeFile('dist/Duckmeta.html',html);
console.log('Standalone workshop: dist/Duckmeta.html');
