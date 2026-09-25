const NOTATION_BY_LETTER = { a: 'arabic', p: 'picto' };
const STYLE_BY_LETTER = { r: 'regular', b: 'bold', i: 'italic' };
const STYLE_KEYS = ['regular', 'bold', 'italic'];
const STYLE_WORDS = { regular: 'обычные', bold: 'жирные', italic: 'курсивные' };
const COLORS = ['#4472c4', '#ed7d31', '#a5a5a5', '#ffc000', '#5b9bd5', '#70ad47', '#264478', '#9e480e', '#636363', '#997300'];
const LINK_PATTERN = /v4(_[ap](\d[rbi])+-\d*)+/g;

const SECTIONS = [
  { notation: 'arabic', title: 'Арабские цифры' },
  { notation: 'picto', title: 'Пиктограммы' },
  { notation: null, title: 'Все вместе' },
];

function findLinks(text) {
  const found = text.match(LINK_PATTERN);
  if (found === null) {
    return [];
  }
  const unique = [];
  for (const link of found) {
    if (!unique.includes(link)) {
      unique.push(link);
    }
  }
  return unique;
}

function decodeRound(part) {
  const notation = NOTATION_BY_LETTER[part[0]];
  const halves = part.substring(1).split('-');
  const itemsText = halves[0];
  const selectedText = halves[1];

  const items = [];
  for (let i = 0; i < itemsText.length; i += 2) {
    const digit = Number(itemsText[i]);
    const style = STYLE_BY_LETTER[itemsText[i + 1]];
    items.push({ digit: digit, style: style });
  }

  const selected = [];
  for (const char of selectedText) {
    selected.push(Number(char));
  }

  return { notation: notation, items: items, selected: selected };
}

function decodeLink(link) {
  const parts = link.split('_');
  const rounds = [];
  for (let i = 1; i < parts.length; i++) {
    rounds.push(decodeRound(parts[i]));
  }
  return rounds;
}

function emptyCounter() {
  return { shown: 0, remembered: 0 };
}

function countRemembered(participants, notation) {
  const result = {
    regular: emptyCounter(),
    bold: emptyCounter(),
    italic: emptyCounter(),
  };

  for (const rounds of participants) {
    for (const round of rounds) {
      if (notation !== null && round.notation !== notation) {
        continue;
      }
      for (const item of round.items) {
        const counter = result[item.style];
        counter.shown += 1;
        if (round.selected.includes(item.digit)) {
          counter.remembered += 1;
        }
      }
    }
  }

  result.special = {
    shown: result.bold.shown + result.italic.shown,
    remembered: result.bold.remembered + result.italic.remembered,
  };
  return result;
}

function share(counter) {
  if (counter.shown === 0) {
    return 0;
  }
  return counter.remembered / counter.shown * 100;
}

function percent(counter) {
  return Math.round(share(counter)) + '%';
}

function verdictHtml(confirmed) {
  if (confirmed) {
    return '<b class="v-yes">подтверждается</b>';
  }
  return '<b class="v-no">не подтверждается</b>';
}

function firstHypothesisConfirmed(counts) {
  return share(counts.special) > share(counts.regular);
}

function secondHypothesisConfirmed(counts) {
  const bold = share(counts.bold);
  return bold > share(counts.italic) && bold > share(counts.regular);
}

function summaryItems(title, counts) {
  const first = firstHypothesisConfirmed(counts);
  const second = secondHypothesisConfirmed(counts);

  const firstDetails = 'с начертанием — ' + percent(counts.special) + ', обычные — ' + percent(counts.regular);
  const secondDetails = 'жирные — ' + percent(counts.bold) + ', курсив — ' + percent(counts.italic) + ', обычные — ' + percent(counts.regular);

  let html = '';
  html += '<li>' + title + ': гипотеза 1 ' + verdictHtml(first) + ' (' + firstDetails + ').</li>';
  html += '<li>' + title + ': гипотеза 2 ' + verdictHtml(second) + ' (' + secondDetails + ').</li>';
  return html;
}

function chartHtml(participants, notation) {
  const single = participants.length === 1;
  const showValues = participants.length <= 10;
  const glyphNotation = notation === null ? 'arabic' : notation;

  const perParticipant = [];
  for (const rounds of participants) {
    perParticipant.push(countRemembered([rounds], notation));
  }

  let groups = '';
  for (const style of STYLE_KEYS) {
    groups += '<div class="vgroup">';
    for (let i = 0; i < perParticipant.length; i++) {
      const value = share(perParticipant[i][style]);
      let color = COLORS[i % COLORS.length];
      if (single) {
        color = 'var(--' + style + ')';
      }
      groups += '<div class="vbar" style="height:' + value + '%;background:' + color + '">';
      if (showValues) {
        groups += '<span>' + Math.round(value) + '</span>';
      }
      groups += '</div>';
    }
    groups += '</div>';
  }

  let axis = '';
  for (let value = 0; value <= 100; value += 25) {
    axis += '<span style="bottom:' + value + '%">' + value + '</span>';
  }

  let labels = '';
  for (const style of STYLE_KEYS) {
    const glyph = renderDigit(5, glyphNotation, style);
    labels += '<span><span class="glyph">' + glyph + '</span>' + STYLES[style] + '</span>';
  }

  let legend = '';
  if (!single) {
    legend += '<div class="vlegend">';
    for (let i = 0; i < participants.length; i++) {
      const color = COLORS[i % COLORS.length];
      legend += '<span><i style="background:' + color + '"></i>№' + (i + 1) + '</span>';
    }
    legend += '</div>';
  }

  let html = '<div class="vchart">';
  html += '<div class="vaxis">' + axis + '</div>';
  html += '<div class="vplot">' + groups + '</div>';
  html += '<div></div>';
  html += '<div class="vlabels">' + labels + '</div>';
  html += '</div>';
  html += legend;
  return html;
}

function conclusionHtml(figureNumber, participants, counts, notation) {
  const sorted = STYLE_KEYS.slice();
  sorted.sort(function (a, b) {
    return share(counts[b]) - share(counts[a]);
  });
  const best = sorted[0];
  const worst = sorted[sorted.length - 1];

  let text = 'Из рисунка ' + figureNumber + ' видно, что ';
  if (participants.length > 1) {
    text += 'в среднем ';
  }
  text += 'лучше всего запоминались ' + STYLE_WORDS[best] + ' цифры (' + percent(counts[best]) + '), ';
  text += 'хуже всего — ' + STYLE_WORDS[worst] + ' (' + percent(counts[worst]) + ').';

  if (participants.length > 1) {
    let specialBetter = 0;
    let boldBetter = 0;
    for (const rounds of participants) {
      const own = countRemembered([rounds], notation);
      if (firstHypothesisConfirmed(own)) {
        specialBetter += 1;
      }
      if (secondHypothesisConfirmed(own)) {
        boldBetter += 1;
      }
    }
    const total = participants.length;
    text += ' Цифры с начертанием запомнились лучше обычных у ' + specialBetter + ' из ' + total + ' участников, ';
    text += 'жирные лучше всех остальных — у ' + boldBetter + ' из ' + total + '.';
  }

  return '<p>' + text + '</p>';
}

function styleTableHtml(counts) {
  let html = '<table class="tbl">';
  html += '<tr><th>Начертание</th><th>Показано цифр</th><th>Запомнено</th><th>Доля запомненных</th></tr>';
  for (const style of STYLE_KEYS) {
    const counter = counts[style];
    html += '<tr>';
    html += '<td>' + STYLES[style] + '</td>';
    html += '<td>' + counter.shown + '</td>';
    html += '<td>' + counter.remembered + '</td>';
    html += '<td>' + percent(counter) + '</td>';
    html += '</tr>';
  }
  html += '</table>';
  return html;
}

function participantsTableHtml(participants) {
  let firstHeader = '<tr><th rowspan="2">№</th>';
  let secondHeader = '<tr>';
  for (const section of SECTIONS) {
    firstHeader += '<th colspan="2">' + section.title + '</th>';
    secondHeader += '<th>обычные</th><th>жирные и курсив</th>';
  }
  firstHeader += '</tr>';
  secondHeader += '</tr>';

  let rows = '';
  for (let i = 0; i < participants.length; i++) {
    rows += '<tr><td>' + (i + 1) + '</td>';
    for (const section of SECTIONS) {
      const counts = countRemembered([participants[i]], section.notation);
      rows += '<td>' + percent(counts.regular) + '</td>';
      rows += '<td>' + percent(counts.special) + '</td>';
    }
    rows += '</tr>';
  }

  return '<table class="tbl">' + firstHeader + secondHeader + rows + '</table>';
}

function renderReport(participants) {
  let summary = '';
  for (const section of SECTIONS) {
    const counts = countRemembered(participants, section.notation);
    summary += summaryItems(section.title, counts);
  }

  let html = '';
  html += '<h2>Коротко</h2>';
  html += '<p>Участников: ' + participants.length + '. ';
  html += 'Гипотеза 1 — цифры с начертанием запоминаются лучше обычных. ';
  html += 'Гипотеза 2 — жирные цифры запоминаются лучше, чем обычные и курсивные.</p>';
  html += '<ul class="short">' + summary + '</ul>';
  html += '<p class="note">План тестирования: 15 раундов с арабскими цифрами, затем 15 с пиктограммами. ';
  html += 'В каждом виде записи 5 раундов, где половина цифр обычные, а половина жирные и курсивные вперемешку; ';
  html += '5 раундов «обычные + жирные»; 5 раундов «обычные + курсив».</p>';
  html += '<p class="note">Как считается: для каждой показанной цифры проверяется, отметил ли её участник. ';
  html += 'Доля запомненных = запомнено ÷ показано × 100%. ';
  html += 'Гипотеза подтверждается, если доля у проверяемого начертания больше, чем у остальных.</p>';

  for (let i = 0; i < SECTIONS.length; i++) {
    const section = SECTIONS[i];
    const number = i + 1;
    const counts = countRemembered(participants, section.notation);
    const name = section.title.toLowerCase();

    let caption = 'Рисунок ' + number + ' — Доля запомненных цифр по начертаниям';
    if (participants.length > 1) {
      caption += ' у каждого участника';
    }
    caption += ', %: ' + name;

    html += '<h2>' + section.title + '</h2>';
    html += '<figure class="fig">';
    html += chartHtml(participants, section.notation);
    html += '<figcaption>' + caption + '</figcaption>';
    html += '</figure>';
    html += conclusionHtml(number, participants, counts, section.notation);
    html += '<div class="fig">';
    html += '<p class="fig-caption">Таблица ' + number + ' — Запомненные цифры по начертаниям: ' + name + '</p>';
    html += styleTableHtml(counts);
    html += '</div>';
  }

  if (participants.length > 1) {
    html += '<h2>По участникам</h2>';
    html += '<div class="fig">';
    html += '<p class="fig-caption">Таблица 4 — Доля запомненных цифр у каждого участника</p>';
    html += participantsTableHtml(participants);
    html += '</div>';
  }

  document.getElementById('report').innerHTML = html;
}

function calculate() {
  const text = document.getElementById('input').value;
  const links = findLinks(text);
  document.getElementById('status').textContent = 'Найдено результатов: ' + links.length + '.';
  document.getElementById('report').innerHTML = '';
  if (links.length === 0) {
    return;
  }

  const participants = [];
  for (const link of links) {
    participants.push(decodeLink(link));
  }
  renderReport(participants);
}

function copyLink() {
  const message = document.getElementById('copy-msg');
  navigator.clipboard.writeText(location.href).then(
    function () {
      message.textContent = 'Ссылка скопирована.';
    },
    function () {
      message.textContent = 'Скопируйте адрес из строки браузера.';
    }
  );
}

function showOwnResult(link) {
  document.getElementById('mine').hidden = false;
  document.getElementById('paste').hidden = true;
  renderReport([decodeLink(link)]);
}

function start() {
  document.getElementById('btn-calc').addEventListener('click', calculate);
  document.getElementById('btn-copy').addEventListener('click', copyLink);

  if (location.hash === '#demo-one') {
    showOwnResult(MOCKS[0]);
    return;
  }

  if (location.hash === '#demo') {
    document.getElementById('input').value = MOCKS.join(' ');
    calculate();
    return;
  }

  const links = findLinks(location.hash);
  if (links.length > 0) {
    showOwnResult(links[0]);
  }
}

start();
