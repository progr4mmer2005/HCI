const SHOW_TIME = { arabic: 3000, picto: 5000 };
const FIXATION_TIME = 800;
const ANSWER_TIME = 20000;
const PAUSE_TIME = 5000;
const ROUNDS_PER_GROUP = 5;

let plan = [];
let finishedRounds = [];
let currentRound = null;
let phase = 'start';
let timerFrame = 0;

function shuffle(list) {
  const result = list.slice();
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const temp = result[i];
    result[i] = result[j];
    result[j] = temp;
  }
  return result;
}

function repeat(value, times) {
  const result = [];
  for (let i = 0; i < times; i++) {
    result.push(value);
  }
  return result;
}

function randomSize() {
  if (Math.random() < 0.5) {
    return 6;
  }
  return 8;
}

function buildPlan() {
  const result = [];
  for (const notation of ['arabic', 'picto']) {
    for (let i = 0; i < ROUNDS_PER_GROUP; i++) {
      result.push({ notation: notation, size: 8, specialStyles: ['bold', 'bold', 'italic', 'italic'] });
    }
    for (const style of ['bold', 'italic']) {
      for (let i = 0; i < ROUNDS_PER_GROUP; i++) {
        const size = randomSize();
        result.push({ notation: notation, size: size, specialStyles: repeat(style, size / 2) });
      }
    }
  }
  return result;
}

function makeRound(roundPlan) {
  const digits = shuffle([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]).slice(0, roundPlan.size);
  const regularStyles = repeat('regular', roundPlan.size / 2);
  const styles = shuffle(regularStyles.concat(roundPlan.specialStyles));

  const items = [];
  for (let i = 0; i < digits.length; i++) {
    items.push({ digit: digits[i], style: styles[i] });
  }
  return { notation: roundPlan.notation, items: items, selected: [] };
}

function showScreen(id) {
  const screens = document.querySelectorAll('.screen');
  for (const screen of screens) {
    screen.hidden = screen.id !== id;
  }
}

function startTimer(label, duration, onEnd) {
  cancelAnimationFrame(timerFrame);
  const endTime = performance.now() + duration;
  document.getElementById('timer-label').textContent = label;

  function tick(now) {
    const left = Math.max(0, endTime - now);
    const seconds = (left / 1000).toFixed(1).replace('.', ',');
    document.getElementById('timer-val').textContent = seconds + ' с';
    document.getElementById('timer-bar').style.width = (left / duration * 100) + '%';
    if (left > 0) {
      timerFrame = requestAnimationFrame(tick);
    } else {
      onEnd();
    }
  }

  timerFrame = requestAnimationFrame(tick);
}

function placeDigits(stage, round) {
  const box = stage.getBoundingClientRect();
  let columns = 3;
  if (box.width >= box.height) {
    columns = 5;
  }
  const rows = 15 / columns;
  const cellWidth = box.width / columns;
  const cellHeight = box.height / rows;
  const size = Math.min(cellWidth, cellHeight, 130) * 0.7;
  const cells = shuffle([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]);

  let html = '';
  for (let i = 0; i < round.items.length; i++) {
    const item = round.items[i];
    const column = cells[i] % columns;
    const row = Math.floor(cells[i] / columns);
    const x = column * cellWidth + (cellWidth - size) * (0.1 + Math.random() * 0.8);
    const y = row * cellHeight + (cellHeight - size) * (0.1 + Math.random() * 0.8);
    const style = 'width:' + size + 'px;height:' + size + 'px;left:' + x + 'px;top:' + y + 'px';
    html += '<div class="obj" style="' + style + '">' + renderDigit(item.digit, round.notation, item.style) + '</div>';
  }
  return html;
}

function startRound() {
  currentRound = makeRound(plan[finishedRounds.length]);
  phase = 'show';
  document.getElementById('progress').textContent = 'Раунд ' + (finishedRounds.length + 1) + ' / ' + plan.length;
  showScreen('screen-show');
  document.body.classList.add('showing');

  const stage = document.getElementById('stage');
  stage.innerHTML = '<div class="fixation">+</div>';

  setTimeout(function () {
    stage.innerHTML = placeDigits(stage, currentRound);
    setTimeout(function () {
      stage.innerHTML = '';
      document.body.classList.remove('showing');
      askAnswer();
    }, SHOW_TIME[currentRound.notation]);
  }, FIXATION_TIME);
}

function askAnswer() {
  phase = 'answer';
  const options = document.getElementById('options');
  options.innerHTML = '';

  for (let digit = 0; digit <= 9; digit++) {
    const button = document.createElement('button');
    button.className = 'opt';
    button.dataset.digit = digit;
    button.innerHTML = renderDigit(digit, currentRound.notation, 'regular');
    button.addEventListener('click', function () {
      toggleDigit(digit);
    });
    options.appendChild(button);
  }

  document.getElementById('feedback').hidden = true;
  document.getElementById('btn-submit').hidden = false;
  document.getElementById('btn-next').hidden = true;
  showScreen('screen-answer');
  startTimer('На ответ осталось', ANSWER_TIME, submitAnswer);
}

function toggleDigit(digit) {
  if (phase !== 'answer') {
    return;
  }
  const button = document.querySelector('.opt[data-digit="' + digit + '"]');
  button.classList.toggle('selected');
}

function submitAnswer() {
  if (phase !== 'answer') {
    return;
  }
  phase = 'feedback';

  const shownDigits = [];
  for (const item of currentRound.items) {
    shownDigits.push(item.digit);
  }

  const selectedButtons = document.querySelectorAll('.opt.selected');
  for (const button of selectedButtons) {
    currentRound.selected.push(Number(button.dataset.digit));
  }
  finishedRounds.push(currentRound);

  let correct = 0;
  const buttons = document.querySelectorAll('.opt');
  for (const button of buttons) {
    const digit = Number(button.dataset.digit);
    const wasShown = shownDigits.includes(digit);
    const wasSelected = currentRound.selected.includes(digit);
    button.disabled = true;
    if (wasShown && wasSelected) {
      button.classList.add('hit');
      correct += 1;
    } else if (wasShown) {
      button.classList.add('miss');
    } else if (wasSelected) {
      button.classList.add('fa');
    }
  }

  const feedback = document.getElementById('feedback');
  feedback.textContent = 'Верно: ' + correct + ' из ' + shownDigits.length;
  feedback.hidden = false;
  document.getElementById('btn-submit').hidden = true;
  document.getElementById('btn-next').hidden = false;

  let label = 'Следующий раунд через';
  if (finishedRounds.length === plan.length) {
    label = 'Результаты через';
  }
  startTimer(label, PAUSE_TIME, goNext);
}

function goNext() {
  if (phase !== 'feedback') {
    return;
  }
  cancelAnimationFrame(timerFrame);
  if (finishedRounds.length < plan.length) {
    startRound();
  } else {
    location.href = 'results.html#' + encodeResult(finishedRounds);
  }
}

function encodeRound(round) {
  let text = round.notation[0];
  for (const item of round.items) {
    text += item.digit + item.style[0];
  }
  text += '-' + round.selected.join('');
  return text;
}

function encodeResult(rounds) {
  let text = 'v4';
  for (const round of rounds) {
    text += '_' + encodeRound(round);
  }
  return text;
}

function startTest() {
  plan = buildPlan();
  finishedRounds = [];
  startRound();
}

function handleKey(event) {
  if (phase === 'answer' && event.key >= '0' && event.key <= '9') {
    toggleDigit(Number(event.key));
  } else if (phase === 'answer' && event.key === 'Enter') {
    submitAnswer();
  } else if (phase === 'feedback' && event.key === 'Enter') {
    goNext();
  }
}

document.getElementById('legend-arabic').innerHTML = renderDigit(5, 'arabic', 'regular');
document.getElementById('legend-picto').innerHTML = renderDigit(5, 'picto', 'regular');
document.getElementById('btn-start').addEventListener('click', startTest);
document.getElementById('btn-submit').addEventListener('click', submitAnswer);
document.getElementById('btn-next').addEventListener('click', goNext);
document.addEventListener('keydown', handleKey);
