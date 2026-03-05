import puppeteer from 'puppeteer';

/**
 * Drop-in API endpoint to generate PDFs from URLs or raw HTML.
 * Perfect for invoices, reports, or tickets.
 */
export async function POST(req: Request) {
    try {
        const { html, url, filename = 'document.pdf', format = 'A4' } = await req.json();

        if (!html && !url) {
            return new Response('Provide HTML or a URL', { status: 400 });
        }

        // Launch headless Chromium
        const browser = await puppeteer.launch({
            headless: 'new',
            args: ['--no-sandbox', '--disable-setuid-sandbox'], // Required for Docker/Serverless
        });

        const page = await browser.newPage();

        // Set content or navigate to URL
        if (html) {
            await page.setContent(html, { waitUntil: 'networkidle0' });
        } else if (url) {
            await page.goto(url, { waitUntil: 'networkidle0' });
        }

        // Generate PDF buffer
        const pdfBuffer = await page.pdf({
            format: format,
            printBackground: true,
            margin: { top: '20px', right: '20px', bottom: '20px', left: '20px' }
        });

        await browser.close();

        // Return the PDF to the client
        return new Response(pdfBuffer, {
            status: 200,
            headers: {
                'Content-Type': 'application/pdf',
                'Content-Disposition': `attachment; filename="${filename}"`
            }
        });

    } catch (error) {
        console.error('PDF Generation Error:', error);
        return new Response('Error generating PDF', { status: 500 });
    }
}
