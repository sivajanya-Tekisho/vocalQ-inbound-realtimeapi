const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

async function convertHTMLtoPDF(htmlPath, pdfPath) {
    console.log(`Converting ${htmlPath} to PDF...`);

    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    // Load the HTML file
    const htmlContent = fs.readFileSync(htmlPath, 'utf8');
    await page.setContent(htmlContent, { waitUntil: 'networkidle0' });

    // Generate PDF with proper settings
    await page.pdf({
        path: pdfPath,
        format: 'A4',
        printBackground: true,
        margin: {
            top: '20mm',
            right: '15mm',
            bottom: '20mm',
            left: '15mm'
        }
    });

    await browser.close();
    console.log(`✓ PDF created: ${pdfPath}`);
}

async function main() {
    const backendHTML = path.join(__dirname, 'backend', 'docs', 'backend_documentation.html');
    const backendPDF = path.join(__dirname, 'backend', 'docs', 'backend_documentation.pdf');

    const frontendHTML = path.join(__dirname, 'frontend', 'docs', 'frontend_documentation.html');
    const frontendPDF = path.join(__dirname, 'frontend', 'docs', 'frontend_documentation.pdf');

    try {
        await convertHTMLtoPDF(backendHTML, backendPDF);
        await convertHTMLtoPDF(frontendHTML, frontendPDF);
        console.log('\n✓ All documentation converted to PDF successfully!');
    } catch (error) {
        console.error('Error converting to PDF:', error);
        process.exit(1);
    }
}

main();
