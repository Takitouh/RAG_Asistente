import '@testing-library/jest-dom';

// Polyfill para jsdom en tests
if (typeof window !== 'undefined') {
  window.HTMLElement.prototype.scrollIntoView = function () {};
}

