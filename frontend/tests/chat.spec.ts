import { test, expect } from '@playwright/test';
test('real chat to CLI workflow and exported result', async ({page}) => {
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'Big ideas.'})).toBeVisible();
 await page.getByLabel('Describe a website task').fill('Crawl https://example.com, extract important information, give me a summary, and return JSON.');
 await page.getByRole('button',{name:'Send message'}).click();
 await expect(page.getByRole('heading',{name:'Example Domain'})).toBeVisible({timeout:90000});
 await expect(page.getByText('Your website analysis is ready.')).toBeVisible();
 await page.screenshot({path:'test-results/agentflow-summary.png', fullPage:true});
 await page.getByRole('tab',{name:'Execution logs'}).click();
 await expect(page.getByText('$ python -m backend.cli.site_crawler', {exact:false})).toBeVisible();
 await expect(page.getByText('Exit code: 0', {exact:false})).toBeVisible();
 await page.getByRole('tab',{name:'JSON',exact:true}).click();
 await expect(page.getByText('task_id:',{exact:true})).toBeVisible();
 const [download] = await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Export JSON'}).click()]);
 expect(download.suggestedFilename()).toMatch(/^task_.*\.json$/);
 await page.screenshot({path:'test-results/agentflow-completed.png', fullPage:true});
});
test('invalid local target fails visibly', async ({page}) => {
 await page.goto('/');
 await page.getByLabel('Describe a website task').fill('Crawl http://127.0.0.1 and summarize the website.');
 await page.getByRole('button',{name:'Send message'}).click();
 await expect(page.getByRole('heading',{name:'Unable to complete this task'})).toBeVisible();
 await expect(page.getByText('Private, reserved, and local addresses are blocked.',{exact:true})).toBeVisible();
});
test('mobile welcome and settings', async ({page}) => {
 await page.setViewportSize({width:390,height:844});
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'Big ideas.'})).toBeVisible();
 await page.screenshot({path:'test-results/agentflow-welcome.png', fullPage:true});
 await page.getByRole('button',{name:'Open navigation'}).click();
 await page.getByRole('button',{name:'Settings',exact:true}).click();
 await expect(page.getByRole('dialog',{name:'Settings'})).toBeVisible();
 await page.screenshot({path:'test-results/agentflow-mobile.png', fullPage:true});
});
test('mobile cancellation returns a cancelled task', async ({page}) => {
 await page.setViewportSize({width:390,height:844});
 await page.goto('/');
 await page.getByLabel('Describe a website task').fill('Crawl https://example.com 5 pages and summarize the website.');
 await page.getByRole('button',{name:'Send message'}).click();
 await page.getByRole('button',{name:'Cancel',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Execution cancelled'})).toBeVisible();
});
