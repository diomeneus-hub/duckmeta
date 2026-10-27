import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { decode } from 'fast-png';
test('edit, undo, preview, and export actual PNG bytes',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await expect(page.locator('#status')).toContainText('wizard.png loaded');
 await expect(page.locator('.stack-item')).toHaveCount(11);
 await page.getByRole('slider',{name:'Horizontal',exact:true}).fill('134');
 await expect(page.getByRole('spinbutton',{name:'Raw green'})).toHaveValue('134');
 await page.getByRole('button',{name:'Undo',exact:true}).click();await expect(page.getByRole('spinbutton',{name:'Raw green'})).toHaveValue('128');
 await page.getByRole('button',{name:'Redo',exact:true}).click();await expect(page.getByRole('spinbutton',{name:'Raw green'})).toHaveValue('134');
 const before=await page.locator('#stage').evaluate((c:HTMLCanvasElement)=>c.toDataURL());
 await page.getByRole('button',{name:'Run',exact:true}).click();await page.waitForTimeout(350);
 const after=await page.locator('#stage').evaluate((c:HTMLCanvasElement)=>c.toDataURL());expect(after).not.toBe(before);
 await page.getByRole('button',{name:'Quack!',exact:false}).click();await expect(page.locator('#particle-count')).not.toHaveText('0');
 await page.getByRole('button',{name:'Blue duck',exact:true}).click();await expect(page.getByRole('button',{name:'Blue duck',exact:true})).toHaveAttribute('aria-pressed','true');
 await page.getByRole('button',{name:'Add modifier',exact:false}).click();await page.getByRole('textbox',{name:'Search modifiers'}).fill('Use duck color');await page.locator('.catalog-item').click();await expect(page.locator('.stack-item')).toHaveCount(12);
 const download=page.waitForEvent('download');await page.locator('#export').click();const file=await download;const png=decode(readFileSync((await file.path())!));expect(png.width).toBe(97);expect(png.height).toBe(56);expect([...png.data.slice(96*4,97*4)]).toEqual([1,134,128,255]);
 const source=decode(readFileSync('public/assets/wizard.png'));for(let y=0;y<56;y++)expect([...png.data.slice(y*97*4,(y*97+96)*4)]).toEqual([...source.data.slice(y*96*4,(y+1)*96*4)]);
 expect(errors).toEqual([]);await page.getByRole('button',{name:'Idle',exact:true}).click();await page.screenshot({path:'test-results/workshop-desktop.png',fullPage:true});
});
test('import metadata, raw editing, removal and invalid file handling',async({page})=>{
 await page.goto('/');await expect(page.locator('#status')).toContainText('loaded');
 await page.locator('#file').setInputFiles('public/assets/wizard.png');await expect(page.locator('.stack-item')).toHaveCount(0);
 await page.locator('#add').click();await page.getByRole('textbox',{name:'Search modifiers'}).fill('Particle preset');await page.locator('.catalog-item').click();
 await page.getByLabel('Behavior',{exact:true}).selectOption('3');await expect(page.getByRole('spinbutton',{name:'Raw blue'})).toHaveValue('3');
 await page.getByRole('spinbutton',{name:'Raw green'}).fill('255');await page.getByRole('spinbutton',{name:'Raw green'}).press('Tab');
 const promise=page.waitForEvent('download');await page.locator('#export').click();const dl=await promise;
 await page.locator('#file').setInputFiles((await dl.path())!);await expect(page.locator('.stack-item')).toHaveCount(1);await expect(page.getByLabel('Behavior',{exact:true})).toHaveValue('3');
 await page.locator('#file').setInputFiles({name:'invalid.png',mimeType:'image/png',buffer:Buffer.from('not png')});await expect(page.locator('#status')).toContainText('Could not import');await expect(page.locator('.stack-item')).toHaveCount(1);
 await page.getByRole('button',{name:'Remove modifier',exact:false}).click();await expect(page.locator('.stack-item')).toHaveCount(0);
 await page.locator('#undo').click();await expect(page.locator('.stack-item')).toHaveCount(1);
});
test('mobile layout stays usable and help opens',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');await expect(page.locator('#status')).toContainText('loaded');
 const sizes=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,width:innerWidth}));expect(sizes.scroll).toBe(sizes.width);
 await page.locator('#reference').click();await expect(page.locator('#help-dialog')).toBeVisible();await page.getByRole('button',{name:'Close help'}).click();
 await page.screenshot({path:'test-results/workshop-mobile.png',fullPage:true});
});
test('paused preview reacts to hat offset and recoloring without advancing simulation',async({page})=>{
 await page.goto('/');await expect(page.locator('#status')).toContainText('loaded');
 await page.getByRole('button',{name:'Pause preview',exact:true}).click();
 const pixels=()=>page.locator('#stage').evaluate((c:HTMLCanvasElement)=>c.toDataURL());
 await page.waitForTimeout(50);const original=await pixels();await page.waitForTimeout(100);expect(await pixels()).toBe(original);
 await page.getByRole('slider',{name:'Horizontal',exact:true}).fill('144');await page.waitForTimeout(50);expect(await pixels()).not.toBe(original);
 await page.locator('#undo').click();await page.waitForTimeout(50);expect(await pixels()).toBe(original);
 await page.getByRole('button',{name:'Pink duck',exact:true}).click();await page.waitForTimeout(50);expect(await pixels()).not.toBe(original);
});
test('standalone bundle works offline with all assets embedded',async({page,context})=>{
 await context.setOffline(true);
 await page.route('**/standalone.html',route=>route.fulfill({contentType:'text/html',body:readFileSync('dist/Duckmeta.html')}));
 await page.goto('/standalone.html');await expect(page.locator('#status')).toContainText('wizard.png loaded');
 await expect(page.locator('.stack-item')).toHaveCount(11);
 await page.getByRole('button',{name:'Quack!',exact:false}).click();await expect(page.locator('#particle-count')).not.toHaveText('0');
 const promise=page.waitForEvent('download');await page.locator('#export').click();const dl=await promise;const png=decode(readFileSync((await dl.path())!));expect(png.width).toBe(97);
});
