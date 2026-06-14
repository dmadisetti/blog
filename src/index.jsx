import React from 'react';
import { createRoot } from 'react-dom/client';
import VimNavigation from './components/VimNavigation';

let root = null;
let container = null;

function isDesktopWithKeyboard() {
  const hasFinePointer = window.matchMedia('(pointer: fine)').matches;
  const canHover = window.matchMedia('(hover: hover)').matches;
  return hasFinePointer && canHover;
}

// Resolve the content column in PRIORITY order. A single
// `querySelector('.md-content__inner, article, main, .content')` returns the
// first element in *document order* matching any selector — which is `main`,
// and `main` wraps Material's sidebars too. That made vim index sidebar/nav
// items ("cursor starts in the sidebar"). Try the tightest selector first.
function findContentArea() {
  return (
    document.querySelector('.md-content__inner') ||
    document.querySelector('article.md-content__inner') ||
    document.querySelector('.md-content article') ||
    document.querySelector('main .md-content') ||
    document.querySelector('main')
  );
}

function extractContentBlocks() {
  // Find main content area (MkDocs Material structure)
  const contentArea = findContentArea();
  if (!contentArea) {
    console.warn('Vim navigation: Could not find content area');
    return [];
  }

  // Blog index / listing ONLY: treat each whole post as ONE block, so the
  // cursor selects the full post rather than its individual spans. We key on
  // `.md-post--excerpt` (the listing form) — a single post *page* is also a
  // `.md-post`, but without `--excerpt`, so it falls through to per-element
  // (block-level) nav + trail. (The caller drops the trail for these large
  // blocks.)
  const posts = contentArea.querySelectorAll('.md-post--excerpt');
  if (posts.length > 0) {
    const postBlocks = [];
    posts.forEach((el, idx) => {
      const text = el.textContent.trim();
      if (text.length > 0) {
        postBlocks.push({ id: `block-${idx}`, text, element: el, type: 'post' });
      }
    });
    if (postBlocks.length > 0) {
      return postBlocks;
    }
  }

  // Extract text elements
  const elements = contentArea.querySelectorAll('p, h1, h2, h3, h4, h5, h6, pre, blockquote, li');
  const blocks = [];

  elements.forEach((el, idx) => {
    const text = el.textContent.trim();
    if (text.length > 0) {
      blocks.push({
        id: `block-${idx}`,
        text: text,
        element: el,
        type: el.tagName.toLowerCase()
      });
    }
  });

  if (blocks.length === 0) {
    console.warn('Vim navigation: No content blocks found');
  }

  return blocks;
}

function initializeVimNavigation() {
  // Check if we should enable vim navigation
  if (!isDesktopWithKeyboard()) {
    console.log('Vim navigation: Disabled (mobile/touch device detected)');
    return;
  }

  // Extract content blocks
  const blocks = extractContentBlocks();
  if (blocks.length === 0) {
    return;
  }

  // Find content area to attach canvas to
  const contentArea = document.querySelector('.md-content__inner, article, main, .content');
  if (!contentArea) {
    console.warn('Vim navigation: Could not find content area for canvas');
    return;
  }

  // Ensure content area has relative positioning for absolute children
  if (window.getComputedStyle(contentArea).position === 'static') {
    contentArea.style.position = 'relative';
  }

  // Create container for React app if it doesn't exist
  if (!container) {
    container = document.createElement('div');
    container.id = 'vim-navigation-root';
    container.style.position = 'absolute';
    container.style.top = '0';
    container.style.left = '0';
    container.style.width = '100%';
    container.style.height = '100%';
    container.style.pointerEvents = 'none';
    container.style.zIndex = '9999';
    contentArea.appendChild(container);
  }

  // Mount React component
  if (!root) {
    root = createRoot(container);
  }

  // Whole-post blocks (the listing) drop the trail; element-level pages keep it.
  const largeBlockMode = blocks.some((b) => b.type === 'post');
  root.render(<VimNavigation blocks={blocks} disableTrail={largeBlockMode} />);

  console.log(`Vim navigation: Initialized with ${blocks.length} blocks`);
}

function cleanupVimNavigation() {
  if (root) {
    root.unmount();
    root = null;
  }

  if (container) {
    container.remove();
    container = null;
  }
}

// Initialize when DOM is ready
function setup() {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeVimNavigation);
  } else {
    initializeVimNavigation();
  }
}

// Handle MkDocs Material instant loading.
// `document$` is a global Material exposes (it does NOT expose `rxjs`), and it
// fires on every navigation including instant loads. Requiring `rxjs` here was
// a bug: it's never a global, so this branch never ran and we fell back to the
// MutationObserver — which thrashes on every DOM mutation (e.g. marimo islands
// hydrating), so the cursor never settled on blog/landing pages.
if (typeof document$ !== 'undefined') {
  document$.subscribe(() => {
    cleanupVimNavigation();
    // Wait a bit for content to render
    setTimeout(initializeVimNavigation, 100);
  });
} else {
  // Fallback: listen for URL changes
  let lastUrl = location.href;
  new MutationObserver(() => {
    const url = location.href;
    if (url !== lastUrl) {
      lastUrl = url;
      cleanupVimNavigation();
      setTimeout(initializeVimNavigation, 100);
    }
  }).observe(document, { subtree: true, childList: true });
}

// Initial setup
setup();
