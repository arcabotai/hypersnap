import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const required = [
  'hypersnap doctor',
  'curl -fsSL https://hypersnap.org/install.sh | bash',
  'hypersnap share',
  'No surprise chainsaw',
  '$SNAP is live',
  'hypria.app',
  '200,000,000,000',
  'Retro rewards allocation',
  '33,000,000',
  'Proof of Work Tokenization',
  '0x49B5a631F54927c0007232844f06FE18cbf69786',
  'View on Dexscreener',
];
for (const needle of required) {
  if (!html.includes(needle)) {
    console.error(`Missing required copy: ${needle}`);
    process.exit(1);
  }
}
console.log('site validation ok');
