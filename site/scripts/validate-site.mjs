import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const required = [
  'hypersnap doctor',
  'curl -fsSL https://hypersnap.org/install.sh | bash',
  'hypersnap share',
  'No surprise chainsaw',
];
for (const needle of required) {
  if (!html.includes(needle)) {
    console.error(`Missing required copy: ${needle}`);
    process.exit(1);
  }
}
console.log('site validation ok');
