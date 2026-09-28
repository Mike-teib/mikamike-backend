import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 375, height: 812 } });

try {
  await page.goto('http://127.0.0.1:4173', { waitUntil: 'networkidle' });

  await page.getByRole('button', { name: /Interface Mika IA/i }).click();
  await page.getByText(/Énoncé en cours/i).waitFor({ state: 'visible' });

  const beforeOverflow = await page.evaluate(() => ({
    innerWidth: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth
  }));
  if (beforeOverflow.scrollWidth > beforeOverflow.innerWidth + 1) {
    throw new Error(`Débordement horizontal avant outils: ${JSON.stringify(beforeOverflow)}`);
  }

  const mic = page.getByRole('button', { name: /Activer la dictée vocale/i });
  if (!(await mic.isVisible())) throw new Error('Bouton micro absent à 375 px');

  await page.getByRole('button', { name: /Basculer le clavier mathématique/i }).click();
  const dock = page.locator('.math-keyboard-dock');
  await dock.waitFor({ state: 'visible' });
  const compactBox = await dock.boundingBox();
  if (!compactBox || compactBox.width > 375 || compactBox.height > 150) {
    throw new Error(`Clavier compact hors limites: ${JSON.stringify(compactBox)}`);
  }

  if (!(await page.getByText(/Énoncé en cours/i).isVisible())) {
    throw new Error('Énoncé masqué par le clavier compact');
  }

  await page.getByRole('button', { name: /Agrandir le clavier mathématique/i }).click();
  const expandedBox = await dock.boundingBox();
  if (!expandedBox || expandedBox.width > 375 || expandedBox.height > 225) {
    throw new Error(`Clavier étendu hors limites: ${JSON.stringify(expandedBox)}`);
  }

  await page.getByRole('button', { name: /Réduire le clavier mathématique/i }).click();
  await page.getByRole('button', { name: /Fermer le clavier mathématique/i }).click();

  await page.getByRole('button', { name: /Basculer la calculatrice/i }).click();
  const tools = page.locator('.right-sidebar');
  await tools.waitFor({ state: 'visible' });
  const toolsBox = await tools.boundingBox();
  if (!toolsBox || toolsBox.x < -1 || toolsBox.x + toolsBox.width > 376) {
    throw new Error(`Panneau outils hors viewport: ${JSON.stringify(toolsBox)}`);
  }

  const afterOverflow = await page.evaluate(() => ({
    innerWidth: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth
  }));
  if (afterOverflow.scrollWidth > afterOverflow.innerWidth + 1) {
    throw new Error(`Débordement horizontal après outils: ${JSON.stringify(afterOverflow)}`);
  }

  if (!(await page.getByText(/Énoncé en cours/i).isVisible())) {
    throw new Error('Énoncé masqué après ouverture des outils');
  }

  await page.screenshot({ path: '/tmp/mikamike-ui-v3-mobile-375.png', fullPage: true });

  console.log('UI_V3_MOBILE_375=PASS');
  console.log('NO_HORIZONTAL_OVERFLOW=PASS');
  console.log('PINNED_EXERCISE_WITH_KEYBOARD=PASS');
  console.log('COMPACT_KEYBOARD=PASS');
  console.log('COMPACT_TOOLS=PASS');
  console.log('MICROPHONE_CONTROL_VISIBLE=PASS');
} finally {
  await browser.close();
}
