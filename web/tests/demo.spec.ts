import {test, expect} from '@playwright/test';

test('retrieves evidence, links sources and abstains outside the corpus', async ({page})=>{
  await page.goto('/');
  await expect(page.getByRole('link', {name:'rag / evidence explorer'})).toBeVisible();
  await page.getByRole('button', {name:'Run query'}).click();
  await expect(page.locator('article').first()).toBeVisible();
  await expect(page.locator('article a', {hasText:'Human oversight'}).first()).toBeVisible();
  await page.screenshot({path:'../docs/demo.png', fullPage:true});
  await page.getByLabel('Your research question').fill('How do I bake banana bread?');
  await page.getByRole('button', {name:'Run query'}).click();
  await expect(page.getByText('No sufficiently matching evidence', {exact:false})).toBeVisible();
  await expect(page.locator('article')).toHaveCount(0);
});

test('mobile layout fits the viewport', async ({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await expect(page.getByRole('button', {name:'Run query'})).toBeVisible();
});
