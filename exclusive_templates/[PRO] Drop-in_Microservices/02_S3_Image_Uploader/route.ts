// npm install @aws-sdk/client-s3 sharp
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import sharp from 'sharp';
import crypto from 'crypto';

// Initialize DigitalOcean Spaces / AWS S3 client
const s3 = new S3Client({
    endpoint: process.env.SPACES_ENDPOINT,
    region: 'us-east-1',
    credentials: {
        accessKeyId: process.env.SPACES_KEY,
        secretAccessKey: process.env.SPACES_SECRET
    }
});

/**
 * Drop-in S3 Image Uploader & Optimizer API
 * Receives FormData, optimizes with Sharp (WebP conversion), and uploads to CDN.
 */
export async function POST(req: Request) {
    try {
        const formData = await req.formData();
        const file = formData.get('file') as File;

        if (!file) return new Response('No file uploaded', { status: 400 });

        const buffer = Buffer.from(await file.arrayBuffer());

        // Optimize Image using Sharp (Compresses JPEG to WebP, auto-rotates)
        const optimizedBuffer = await sharp(buffer)
            .rotate()
            .resize({ width: 1200, withoutEnlargement: true }) // Max width 1200px
            .webp({ quality: 80 }) // Compress and convert to WebP
            .toBuffer();

        // Generate unique content hash filename
        const hash = crypto.createHash('md5').update(optimizedBuffer).digest('hex');
        const fileName = `uploads/${hash}.webp`;

        // Upload to Bucket
        await s3.send(new PutObjectCommand({
            Bucket: process.env.SPACES_BUCKET_NAME,
            Key: fileName,
            Body: optimizedBuffer,
            ContentType: 'image/webp',
            ACL: 'public-read' // Make publicly accessible via CDN
        }));

        // Return the final CDN URL
        const publicUrl = `https://${process.env.SPACES_BUCKET_NAME}.${process.env.SPACES_ENDPOINT?.replace('https://', '')}/${fileName}`;
        return new Response(JSON.stringify({ url: publicUrl }), { status: 200 });

    } catch (error) {
        console.error('S3 Upload Error:', error);
        return new Response('Error uploading file', { status: 500 });
    }
}
