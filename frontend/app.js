const form = document.querySelector('#chat-form');
const input = document.querySelector('#question');
const messages = document.querySelector('#messages');
const sendButton = document.querySelector('.send-button');
const clearButton = document.querySelector('#clear-chat');
const suggestionBlock = document.querySelector('#suggestion-block');

let history = [];

function scrollToLatest() {
  messages.scrollTop = messages.scrollHeight;
}

function renderAssistantText(content) {
  const escaped = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  const inlineMarkup = (text) => text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>');

  const lines = escaped.split('\n');
  const rendered = [];
  let index = 0;

  while (index < lines.length) {
    if (lines[index].startsWith('|') && index + 1 < lines.length && /^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$/.test(lines[index + 1])) {
      const cells = (line) => line.replace(/^\||\|$/g, '').split('|').map((cell) => inlineMarkup(cell.trim()));
      const header = cells(lines[index]);
      const rows = [];
      index += 2;
      while (index < lines.length && lines[index].startsWith('|')) {
        rows.push(cells(lines[index]));
        index += 1;
      }
      rendered.push(`<div class="table-wrap"><table><thead><tr>${header.map((cell) => `<th>${cell}</th>`).join('')}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
      continue;
    }

    if (/^#{1,3}\s/.test(lines[index])) {
      rendered.push(`<h3>${inlineMarkup(lines[index].replace(/^#{1,3}\s/, ''))}</h3>`);
    } else if (/^[-*]\s/.test(lines[index])) {
      const items = [];
      while (index < lines.length && /^[-*]\s/.test(lines[index])) {
        items.push(`<li>${inlineMarkup(lines[index].replace(/^[-*]\s/, ''))}</li>`);
        index += 1;
      }
      rendered.push(`<ul>${items.join('')}</ul>`);
      continue;
    } else if (lines[index].trim()) {
      rendered.push(`<p>${inlineMarkup(lines[index])}</p>`);
    }
    index += 1;
  }

  return rendered.join('');
}

function addMessage(role, content) {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role === 'user' ? 'user-message' : 'assistant-message'}`;
  const avatar = role === 'user' ? 'You' : 'S';
  wrapper.innerHTML = `
    <div class="avatar ${role === 'user' ? 'user-avatar' : ''}">${avatar}</div>
    <div class="message-content">
      <div class="message-label">${role === 'user' ? 'You' : 'StockBot'} <span>now</span></div>
      <div class="bubble"></div>
    </div>`;
  const bubble = wrapper.querySelector('.bubble');
  if (role === 'assistant') {
    bubble.innerHTML = renderAssistantText(content);
  } else {
    bubble.textContent = content;
  }
  messages.appendChild(wrapper);
  scrollToLatest();
}

function addTyping() {
  const wrapper = document.createElement('div');
  wrapper.className = 'message assistant-message';
  wrapper.id = 'typing';
  wrapper.innerHTML = '<div class="avatar">S</div><div class="message-content"><div class="message-label">StockBot <span>thinking</span></div><div class="bubble typing"><i></i><i></i><i></i></div></div>';
  messages.appendChild(wrapper);
  scrollToLatest();
}

function removeTyping() {
  document.querySelector('#typing')?.remove();
}

async function ask(question) {
  const trimmedQuestion = question.trim();
  if (!trimmedQuestion || sendButton.disabled) return;

  addMessage('user', trimmedQuestion);
  history.push({ role: 'user', content: trimmedQuestion });
  input.value = '';
  input.style.height = 'auto';
  suggestionBlock?.remove();
  sendButton.disabled = true;
  addTyping();

  try {
    const response = await fetch('/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: trimmedQuestion, history: history.slice(0, -1) })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'The assistant could not answer right now.');

    removeTyping();
    addMessage('assistant', data.answer || 'I did not receive an answer.');
    history.push({ role: 'assistant', content: data.answer || '' });
  } catch (error) {
    removeTyping();
    addMessage('assistant', `I could not complete that request. ${error.message}`);
    history.pop();
  } finally {
    sendButton.disabled = false;
    input.focus();
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  ask(input.value);
});

input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = `${Math.min(input.scrollHeight, 130)}px`;
});

document.querySelectorAll('.suggestion').forEach((button) => {
  button.addEventListener('click', () => ask(button.dataset.question));
});

clearButton.addEventListener('click', () => {
  history = [];
  messages.innerHTML = `
    <div class="message assistant-message welcome-message">
      <div class="avatar">S</div>
      <div class="message-content">
        <div class="message-label">StockBot <span>now</span></div>
        <div class="bubble">Hi, I’m StockBot. Ask me to explore a stock, compare ETFs, or explain an investing concept.</div>
      </div>
    </div>`;
  input.focus();
});
