const STYLES = {
  regular: 'Обычное',
  bold: 'Жирное',
  italic: 'Курсив',
};

const INK = '#1f2328';
const DOT_POSITIONS = [28, 50, 72];

const DOTS_BY_DIGIT = {
  0: [],
  1: [4],
  2: [0, 8],
  3: [0, 4, 8],
  4: [0, 2, 6, 8],
  5: [0, 2, 4, 6, 8],
  6: [0, 2, 3, 5, 6, 8],
  7: [0, 2, 3, 4, 5, 6, 8],
  8: [0, 1, 2, 3, 5, 6, 7, 8],
  9: [0, 1, 2, 3, 4, 5, 6, 7, 8],
};

function arabicSvg(digit, style) {
  let weight = 'font-weight="400"';
  if (style === 'bold') {
    weight = 'font-weight="700" stroke="' + INK + '" stroke-width="1.5"';
  }

  let slant = '';
  if (style === 'italic') {
    slant = 'transform="translate(50 54) skewX(-22) translate(-50 -54)"';
  }

  return '<text x="50" y="54" text-anchor="middle" dominant-baseline="middle" ' +
    'font-family="Arial, Helvetica, sans-serif" font-size="84" fill="' + INK + '" ' +
    weight + ' ' + slant + '>' + digit + '</text>';
}

function pictoSvg(digit, style) {
  let frameWidth = 2.5;
  let dotRadius = 7;
  if (style === 'bold') {
    frameWidth = 7;
    dotRadius = 10;
  }

  let slant = '';
  if (style === 'italic') {
    slant = 'transform="translate(50 50) skewX(-14) translate(-50 -50)"';
  }

  let dots = '';
  for (const index of DOTS_BY_DIGIT[digit]) {
    const x = DOT_POSITIONS[index % 3];
    const y = DOT_POSITIONS[Math.floor(index / 3)];
    dots += '<circle cx="' + x + '" cy="' + y + '" r="' + dotRadius + '" fill="' + INK + '"/>';
  }

  const frame = '<rect x="9" y="9" width="82" height="82" rx="14" fill="none" stroke="' + INK + '" stroke-width="' + frameWidth + '"/>';
  return '<g ' + slant + '>' + frame + dots + '</g>';
}

function renderDigit(digit, notation, style) {
  let body;
  if (notation === 'arabic') {
    body = arabicSvg(digit, style);
  } else {
    body = pictoSvg(digit, style);
  }
  return '<svg viewBox="0 0 100 100" overflow="visible" xmlns="http://www.w3.org/2000/svg">' + body + '</svg>';
}
