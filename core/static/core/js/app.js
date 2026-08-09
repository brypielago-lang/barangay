document.querySelectorAll('textarea').forEach(el => el.addEventListener('input', () => { el.style.height = 'auto'; el.style.height = `${el.scrollHeight}px`; }));
