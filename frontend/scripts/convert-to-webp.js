import sharp from 'sharp';
import fs from 'fs';
import path from 'path';

const sourceDirs = [
  path.join(process.cwd(), 'public'),
  path.join(process.cwd(), 'public', 'assets'),
  path.join(process.cwd(), 'src', 'assets')
];

const extensions = ['.jpg', '.jpeg', '.png', '.gif'];

function getImageFiles(dir) {
  const files = [];
  function traverseDirectory(currentDir) {
    const entries = fs.readdirSync(currentDir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        traverseDirectory(fullPath);
      } else if (entry.isFile()) {
        const ext = path.extname(entry.name).toLowerCase();
        if (extensions.includes(ext)) {
          files.push(fullPath);
        }
      }
    }
  }
  traverseDirectory(dir);
  return files;
}

async function convertToWebp(inputPath) {
  const outputPath = inputPath.replace(/\.(jpg|jpeg|png|gif)$/i, '.webp');

  try {
    await sharp(inputPath)
      .webp({ quality: 80 })
      .toFile(outputPath);

    console.log(`✓ Converted: ${path.relative(process.cwd(), inputPath)} → ${path.relative(process.cwd(), outputPath)}`);
    return true;
  } catch (error) {
    console.error(`✗ Failed to convert ${inputPath}:`, error.message);
    return false;
  }
}

async function main() {
  console.log('Starting WebP conversion...');

  let totalFiles = 0;
  let convertedFiles = 0;

  for (const sourceDir of sourceDirs) {
    if (!fs.existsSync(sourceDir)) {
      console.log(`Directory does not exist: ${sourceDir}`);
      continue;
    }

    console.log(`Scanning: ${sourceDir}`);
    const imageFiles = getImageFiles(sourceDir);
    totalFiles += imageFiles.length;

    console.log(`Found ${imageFiles.length} image files`);

    for (const file of imageFiles) {
      if (await convertToWebp(file)) {
        convertedFiles++;
      }
    }
  }

  console.log(`\nConversion complete!`);
  console.log(`Total files processed: ${totalFiles}`);
  console.log(`Successfully converted: ${convertedFiles}`);
  console.log(`Failed: ${totalFiles - convertedFiles}`);
}

main().catch(console.error);