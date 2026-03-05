const { chromium } = require('playwright-extra');
const stealth = require('puppeteer-extra-plugin-stealth')();
chromium.use(stealth);
const fs = require('fs');
const fastcsv = require('fast-csv');

// Load simple proxy array if needed (format: http://user:pass@ip:port)
const PROXIES = [
    // "http://username:password@1.2.3.4:8080"
];

async function run() {
    const proxyStr = PROXIES.length > 0 ? PROXIES[Math.floor(Math.random() * PROXIES.length)] : undefined;

    const browser = await chromium.launch({
        headless: false, // Set to true in production
        proxy: proxyStr ? { server: proxyStr } : undefined
    });

    const page = await browser.newPage();

    // Anti-Bot Evasion Tactics:
    await page.setExtraHTTPHeaders({
        'Accept-Language': 'en-US,en;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    });

    console.log('Navigating to directory...');
    await page.goto('https://example-directory.com', { waitUntil: 'domcontentloaded' });

    // Example Scrape Logic
    const leads = await page.evaluate(() => {
        const results = [];
        document.querySelectorAll('.listing-card').forEach(card => {
            const name = card.querySelector('.name')?.innerText || 'N/A';
            const email = card.querySelector('.email')?.innerText || 'N/A';
            const phone = card.querySelector('.phone')?.innerText || 'N/A';
            results.push({ name, email, phone });
        });
        return results;
    });

    console.log(`Found ${leads.length} leads. Saving to CSV...`);

    // Write to CSV
    const ws = fs.createWriteStream("leads.csv");
    fastcsv.write(leads, { headers: true }).pipe(ws);

    await browser.close();
    console.log('Done!');
}

run().catch(console.error);
