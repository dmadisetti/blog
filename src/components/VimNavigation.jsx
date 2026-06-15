import React, { useEffect, useRef, useState, useCallback } from 'react';
import TrailRenderer from './TrailRenderer';

export default function VimNavigation({ blocks, disableTrail = false }) {
  const [globalCursor, setGlobalCursor] = useState({ blockId: blocks[0]?.id || 'block-0', line: 0, col: 0 });
  const [pendingCount, setPendingCount] = useState(null);
  const [awaitingChar, setAwaitingChar] = useState(null);
  const [awaitingWindowCmd, setAwaitingWindowCmd] = useState(false);
  const [trails, setTrails] = useState([]);
  const [charCursor, setCharCursor] = useState(null);
  const blockDataRef = useRef({});
  const prevCursorPos = useRef(null);
  const lastMoveTime = useRef(0);

  // Calculate wrapped lines and paragraph starts for each block
  useEffect(() => {
    blocks.forEach(block => {
      if (!blockDataRef.current[block.id]) {
        if (block.type === 'post') {
          // Whole-post blocks (the index listing) are ONE unit, so j/k jumps
          // post-to-post instead of crawling a post's wrapped lines.
          blockDataRef.current[block.id] = {
            lines: [block.text],
            paragraphStarts: [0],
            element: block.element,
          };
          return;
        }
        // Wrap at the element's REAL characters-per-line (body is monospace),
        // so logical lines line up with the DOM's visual lines — that's what
        // makes `j`/`k` land directly below/above instead of at an offset.
        const { lines, paragraphStarts } = wrapText(
          block.text,
          computeMaxCharsPerLine(block.element)
        );
        blockDataRef.current[block.id] = {
          lines,
          paragraphStarts,
          element: block.element
        };
      }
    });
  }, [blocks]);

  // Wrap text into lines
  const wrapText = useCallback((text, maxCharsPerLine) => {
    const paragraphs = text.split('\n');
    const lines = [];
    const paragraphStarts = [];

    paragraphs.forEach(paragraph => {
      paragraphStarts.push(lines.length);

      if (paragraph.length === 0) {
        lines.push('');
        return;
      }

      const words = paragraph.split(' ');
      let currentLine = '';

      words.forEach((word) => {
        const testLine = currentLine ? `${currentLine} ${word}` : word;

        if (testLine.length <= maxCharsPerLine) {
          currentLine = testLine;
        } else {
          if (currentLine) {
            lines.push(currentLine);
          }
          if (word.length > maxCharsPerLine) {
            let remaining = word;
            while (remaining.length > maxCharsPerLine) {
              lines.push(remaining.substring(0, maxCharsPerLine));
              remaining = remaining.substring(maxCharsPerLine);
            }
            currentLine = remaining;
          } else {
            currentLine = word;
          }
        }
      });

      if (currentLine) {
        lines.push(currentLine);
      }
    });

    return { lines, paragraphStarts };
  }, []);

  // Helper to get block data
  const getBlockData = useCallback((blockId) => {
    return blockDataRef.current[blockId];
  }, []);

  // Apply CSS class to current block
  useEffect(() => {
    // Clear stale highlights DOCUMENT-WIDE first. Hash-jumps and Material's
    // instant-nav re-inits can leave a `vim-cursor-active` element that isn't
    // in the current `blocks` set, so iterating only `blocks` let highlights
    // pile up after a few clicks. A global sweep keeps exactly one.
    document.querySelectorAll('.vim-cursor-active').forEach((el) => {
      el.classList.remove('vim-cursor-active');
    });

    // Add class to current block
    const currentBlock = blocks.find(b => b.id === globalCursor.blockId);
    if (currentBlock?.element) {
      currentBlock.element.classList.add('vim-cursor-active');
    }
  }, [globalCursor.blockId, blocks]);

  // Jumping to a header (TOC link, permalink, or landing on a #hash) moves the
  // cursor onto that block.
  useEffect(() => {
    const moveToHash = (rawHash) => {
      const id = decodeURIComponent((rawHash || '').replace(/^#/, ''));
      if (!id) return;
      const target = document.getElementById(id);
      if (!target) return;
      // Exact block match first, then the block that CONTAINS the target (e.g.
      // a permalink anchor inside a heading). Never match a block merely
      // contained BY the target — that was highlighting the wrong inner block.
      const block =
        blocks.find((b) => b.element === target) ||
        blocks.find((b) => b.element && b.element.contains(target));
      if (block) {
        setGlobalCursor({ blockId: block.id, line: 0, col: 0 });
      }
    };

    // Intercept intentional clicks on in-page anchors (TOC entries, heading
    // permalinks). Material navigates these via instant-nav/pushState, which
    // does NOT fire `hashchange`. We deliberately do NOT poll location — that
    // would also catch navigation.tracking's scroll updates and fight manual
    // j/k nav.
    const onClick = (e) => {
      const a = e.target.closest && e.target.closest('a[href]');
      if (!a) return;
      let url;
      try {
        url = new URL(a.href, window.location.href);
      } catch (_) {
        return;
      }
      if (url.hash && url.pathname === window.location.pathname) {
        moveToHash(url.hash);
      }
    };
    const onHashOrPop = () => moveToHash(window.location.hash);

    moveToHash(window.location.hash); // landing on a #hash
    document.addEventListener('click', onClick);
    window.addEventListener('hashchange', onHashOrPop);
    window.addEventListener('popstate', onHashOrPop);
    return () => {
      document.removeEventListener('click', onClick);
      window.removeEventListener('hashchange', onHashOrPop);
      window.removeEventListener('popstate', onHashOrPop);
    };
  }, [blocks]);

  // Scroll management (25-75% viewport constraint)
  useEffect(() => {
    const blockData = getBlockData(globalCursor.blockId);
    if (!blockData || !blockData.element) return;

    const element = blockData.element;
    const viewportHeight = window.innerHeight;
    const rect = element.getBoundingClientRect();

    // Calculate cursor position within the block
    // Simple approximation: use element center for now
    const cursorAbsoluteTop = window.scrollY + rect.top + (rect.height * (globalCursor.line / Math.max(1, blockData.lines.length)));
    const cursorViewportTop = cursorAbsoluteTop - window.scrollY;
    const relativePosition = cursorViewportTop / viewportHeight;

    const upperBound = 0.25;
    const lowerBound = 0.75;

    let newScrollTop = null;

    if (relativePosition < upperBound) {
      newScrollTop = cursorAbsoluteTop - (upperBound * viewportHeight);
    } else if (relativePosition > lowerBound) {
      newScrollTop = cursorAbsoluteTop - (lowerBound * viewportHeight);
    }

    if (newScrollTop !== null) {
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      newScrollTop = Math.max(0, Math.min(maxScroll, newScrollTop));

      if (Math.abs(newScrollTop - window.scrollY) > 1) {
        window.scrollTo({
          top: newScrollTop,
          behavior: 'smooth'
        });
      }
    }
  }, [globalCursor, getBlockData]);

  // Position the per-character cursor (terminal block) on element-level pages.
  // Maps the logical (line, col) back to a character index in the block text,
  // then uses a DOM Range to get that character's on-screen rect.
  useEffect(() => {
    // Titles are never cursor-level — they use the block highlight only.
    const block = blocks.find((b) => b.id === globalCursor.blockId);
    const isHeading = block && /^h[1-6]$/.test(block.type || '');
    // The block-entry position (0,0) is implied — don't draw a cursor there.
    // It appears once the user moves within the block, which avoids the
    // stray/offset cursor on first entry (and the "first k is missing" case).
    const atBlockStart = globalCursor.line === 0 && globalCursor.col === 0;
    if (disableTrail || isHeading || atBlockStart) {
      setCharCursor(null);
      return;
    }
    const compute = () => {
      const blockData = getBlockData(globalCursor.blockId);
      const el = blockData?.element;
      const container = document.getElementById('vim-navigation-root');
      if (!el || !container) {
        setCharCursor(null);
        return;
      }
      const idx = charIndexFromCursor(blockData, globalCursor.line, globalCursor.col);
      const rect = getCharRect(el, idx);
      if (!rect) {
        setCharCursor(null);
        return;
      }
      const c = container.getBoundingClientRect();
      setCharCursor({
        left: rect.left - c.left,
        top: rect.top - c.top,
        width: Math.max(rect.width, 7),
        height: rect.height || 18,
      });
    };
    compute();
    window.addEventListener('resize', compute);
    return () => window.removeEventListener('resize', compute);
  }, [globalCursor, blocks, disableTrail, getBlockData]);

  // Create trail segment when cursor moves
  useEffect(() => {
    // Trail removed entirely (too gimmicky). Keep the position ref in sync but
    // never emit trail segments.
    prevCursorPos.current = { ...globalCursor };
    return;
    // eslint-disable-next-line no-unreachable
    if (!prevCursorPos.current) {
      prevCursorPos.current = { ...globalCursor };
      return;
    }

    const now = performance.now();
    if (now - lastMoveTime.current < 50) { // startThreshold
      prevCursorPos.current = { ...globalCursor };
      lastMoveTime.current = now;
      return;
    }

    // Only create trail if cursor actually moved
    if (prevCursorPos.current.blockId !== globalCursor.blockId ||
        prevCursorPos.current.line !== globalCursor.line ||
        prevCursorPos.current.col !== globalCursor.col) {

      const newTrail = {
        from: { ...prevCursorPos.current },
        to: { ...globalCursor },
        startTime: now,
        endTime: now + 300 // Default decay time
      };

      setTrails(prev => [...prev, newTrail]);
    }

    prevCursorPos.current = { ...globalCursor };
    lastMoveTime.current = now;
  }, [globalCursor]);

  // Navigation primitives
  const navigationPrimitives = {
    charLeft: (cursor, getRef, count = 1) => {
      let current = cursor;
      for (let i = 0; i < count; i++) {
        const data = getRef(current.blockId);
        if (!data) return null;

        if (current.col > 0) {
          current = { ...current, col: current.col - 1 };
        } else if (current.line > 0) {
          const newLine = current.line - 1;
          current = { ...current, line: newLine, col: data.lines[newLine]?.length || 0 };
        } else {
          return 'PREV_BLOCK';
        }
      }
      return current;
    },

    charRight: (cursor, getRef, count = 1) => {
      let current = cursor;
      for (let i = 0; i < count; i++) {
        const data = getRef(current.blockId);
        if (!data) return null;

        const lineLength = data.lines[current.line]?.length || 0;
        if (current.col < lineLength) {
          current = { ...current, col: current.col + 1 };
        } else if (current.line < data.lines.length - 1) {
          current = { ...current, line: current.line + 1, col: 0 };
        } else {
          return 'NEXT_BLOCK';
        }
      }
      return current;
    },

    lineUp: (cursor, getRef, count = 1) => {
      const data = getRef(cursor.blockId);
      if (!data) return null;

      const newLine = cursor.line - count;
      if (newLine < 0) {
        return 'PREV_BLOCK';
      }

      return { ...cursor, line: newLine, col: Math.min(cursor.col, data.lines[newLine]?.length || 0) };
    },

    lineDown: (cursor, getRef, count = 1) => {
      const data = getRef(cursor.blockId);
      if (!data) return null;

      const newLine = cursor.line + count;
      if (newLine >= data.lines.length) {
        return 'NEXT_BLOCK';
      }

      return { ...cursor, line: newLine, col: Math.min(cursor.col, data.lines[newLine]?.length || 0) };
    },

    lineStart: (cursor) => {
      return { ...cursor, col: 0 };
    },

    lineEnd: (cursor, getRef) => {
      const data = getRef(cursor.blockId);
      if (!data) return null;
      return { ...cursor, col: data.lines[cursor.line]?.length || 0 };
    },

    blockStart: (cursor) => {
      return { ...cursor, line: 0, col: 0 };
    },

    blockEnd: (cursor, getRef) => {
      const data = getRef(cursor.blockId);
      if (!data) return null;
      const lastLine = data.lines.length - 1;
      return { ...cursor, line: lastLine, col: 0 };
    },

    jumpDown: (cursor, getRef, lines = 5) => {
      const data = getRef(cursor.blockId);
      if (!data) return null;

      const targetLine = cursor.line + lines;

      if (targetLine >= data.lines.length) {
        return 'NEXT_BLOCK';
      }

      // Snap to paragraph start
      const paragraphStart = data.paragraphStarts.findLast(p => p <= targetLine) || 0;
      const nextParaStart = data.paragraphStarts.find(p => p > targetLine) || data.lines.length - 1;

      let newLine;
      if (targetLine === paragraphStart && targetLine < data.lines.length - 1) {
        newLine = Math.min(nextParaStart, data.lines.length - 1);
      } else {
        newLine = paragraphStart;
      }

      return { ...cursor, line: newLine, col: Math.min(cursor.col, data.lines[newLine]?.length || 0) };
    },

    jumpUp: (cursor, getRef, lines = 5) => {
      const data = getRef(cursor.blockId);
      if (!data) return null;

      const targetLine = cursor.line - lines;

      if (targetLine < 0) {
        return 'PREV_BLOCK';
      }

      const newLine = data.paragraphStarts.findLast(p => p <= targetLine) || 0;
      return { ...cursor, line: newLine, col: Math.min(cursor.col, data.lines[newLine]?.length || 0) };
    },

    wordForward: (cursor, getRef, count = 1) => {
      let current = cursor;

      for (let i = 0; i < count; i++) {
        const data = getRef(current.blockId);
        if (!data) return null;

        let { line, col } = current;

        while (line < data.lines.length) {
          const lineText = data.lines[line] || '';

          while (col < lineText.length && lineText[col] !== ' ') {
            col++;
          }

          while (col < lineText.length && lineText[col] === ' ') {
            col++;
          }

          if (col < lineText.length) {
            current = { ...current, line, col };
            break;
          }

          line++;
          col = 0;

          if (line < data.lines.length) {
            const nextLineText = data.lines[line] || '';
            while (col < nextLineText.length && nextLineText[col] === ' ') {
              col++;
            }
            if (col < nextLineText.length) {
              current = { ...current, line, col };
              break;
            }
          }
        }

        if (line >= data.lines.length) {
          return 'NEXT_BLOCK';
        }
      }

      return current;
    },

    wordBackward: (cursor, getRef, count = 1) => {
      let current = cursor;

      for (let i = 0; i < count; i++) {
        const data = getRef(current.blockId);
        if (!data) return null;

        let { line, col } = current;

        if (col > 0) {
          col--;
        } else if (line > 0) {
          line--;
          col = (data.lines[line]?.length || 0);
          if (col > 0) col--;
        } else {
          return 'PREV_BLOCK';
        }

        while (line >= 0) {
          const lineText = data.lines[line] || '';

          while (col >= 0 && lineText[col] === ' ') {
            col--;
          }

          if (col < 0) {
            line--;
            if (line < 0) return 'PREV_BLOCK';
            col = (data.lines[line]?.length || 0) - 1;
            continue;
          }

          while (col >= 0 && lineText[col] !== ' ') {
            col--;
          }

          col++;
          current = { ...current, line, col };
          break;
        }
      }

      return current;
    },

    wordEnd: (cursor, getRef, count = 1) => {
      let current = cursor;

      for (let i = 0; i < count; i++) {
        const data = getRef(current.blockId);
        if (!data) return null;

        let { line, col } = current;
        col++;

        while (line < data.lines.length) {
          const lineText = data.lines[line] || '';

          while (col < lineText.length && lineText[col] === ' ') {
            col++;
          }

          if (col >= lineText.length) {
            line++;
            col = 0;
            if (line >= data.lines.length) return 'NEXT_BLOCK';
            continue;
          }

          while (col < lineText.length && lineText[col] !== ' ') {
            col++;
          }

          col--;
          current = { ...current, line, col };
          break;
        }
      }

      return current;
    },

    findChar: (cursor, getRef, char, count = 1) => {
      const data = getRef(cursor.blockId);
      if (!data) return null;

      const lineText = data.lines[cursor.line] || '';
      let col = cursor.col + 1;
      let found = 0;

      while (col < lineText.length) {
        if (lineText[col] === char) {
          found++;
          if (found === count) {
            return { ...cursor, col };
          }
        }
        col++;
      }

      return cursor;
    },

    blockNext: () => 'NEXT_BLOCK',
    blockPrev: () => 'PREV_BLOCK'
  };

  // Keymap configuration
  const keymap = {
    'h': { primitive: 'charLeft' },
    'l': { primitive: 'charRight' },
    'ArrowLeft': { primitive: 'charLeft' },
    'ArrowRight': { primitive: 'charRight' },
    'j': { primitive: 'lineDown' },
    'k': { primitive: 'lineUp' },
    'ArrowDown': { primitive: 'lineDown' },
    'ArrowUp': { primitive: 'lineUp' },
    'H': { primitive: 'lineStart' },
    'L': { primitive: 'lineEnd' },
    'g': { primitive: 'blockStart' },
    'G': { primitive: 'blockEnd' },
    'ctrl+j': { remap: '5j' },
    'ctrl+k': { remap: '5k' },
    'w': { primitive: 'wordForward' },
    'b': { primitive: 'wordBackward' },
    'e': { primitive: 'wordEnd' },
    'ctrl+l': { primitive: 'wordForward' },
    'ctrl+h': { primitive: 'wordBackward' },
    'f': { awaitChar: 'findChar' },
    'ctrl+w': { awaitWindowCmd: true },
    'Enter': { openLink: true }
  };

  const windowCommandMap = {
    'j': { primitive: 'blockNext' },
    'k': { primitive: 'blockPrev' },
    'ArrowDown': { primitive: 'blockNext' },
    'ArrowUp': { primitive: 'blockPrev' }
  };

  // Execute command
  const executeCommand = useCallback((commandKey, count = 1) => {
    const action = keymap[commandKey];
    if (!action) return;

    if (action.remap) {
      const remapMatch = action.remap.match(/^(\d*)(.+)$/);
      if (remapMatch) {
        const [, remapCountStr, remapKey] = remapMatch;
        const remapCount = remapCountStr ? parseInt(remapCountStr, 10) : 1;
        executeCommand(remapKey, count * remapCount);
      }
      return;
    }

    if (action.awaitChar) {
      setAwaitingChar(action.awaitChar);
      return;
    }

    if (action.awaitWindowCmd) {
      setAwaitingWindowCmd(true);
      return;
    }

    if (action.openLink) {
      const block = blocks.find((b) => b.id === globalCursor.blockId);
      const el = block && block.element;
      if (el) {
        const isPost = block.type === 'post';
        // On the index a post block opens the post in a NEW TAB; elsewhere,
        // open the block's link (honoring its own target).
        const link = isPost
          ? el.querySelector('.md-post__action a[href], a[href]')
          : el.querySelector('a[href]');
        if (link) {
          if (isPost || link.target === '_blank') {
            window.open(link.href, '_blank', 'noopener');
          } else {
            window.location.href = link.href;
          }
        }
      }
      return;
    }

    if (action.primitive) {
      const getRef = (blockId) => blockDataRef.current[blockId];
      const primitive = navigationPrimitives[action.primitive];

      if (!primitive) return;

      let newCursor = primitive(globalCursor, getRef, count);

      if (newCursor === 'NEXT_BLOCK') {
        const currentIdx = blocks.findIndex(b => b.id === globalCursor.blockId);
        if (currentIdx < blocks.length - 1) {
          const nextBlock = blocks[currentIdx + 1];
          newCursor = { blockId: nextBlock.id, line: 0, col: 0 };
        } else {
          return;
        }
      } else if (newCursor === 'PREV_BLOCK') {
        const currentIdx = blocks.findIndex(b => b.id === globalCursor.blockId);
        if (currentIdx > 0) {
          const prevBlock = blocks[currentIdx - 1];
          const prevData = blockDataRef.current[prevBlock.id];
          if (prevData) {
            const lastLine = prevData.lines.length - 1;
            newCursor = {
              blockId: prevBlock.id,
              line: lastLine,
              col: prevData.lines[lastLine]?.length || 0
            };
          }
        } else {
          return;
        }
      }

      if (newCursor) {
        setGlobalCursor(newCursor);
      }
    }
  }, [globalCursor, blocks, navigationPrimitives, keymap]);

  // Handle navigation
  const handleNavigation = useCallback((key, ctrlKey) => {
    if (awaitingWindowCmd) {
      const windowAction = windowCommandMap[key];

      if (windowAction && windowAction.primitive) {
        const getRef = (blockId) => blockDataRef.current[blockId];
        const primitive = navigationPrimitives[windowAction.primitive];

        if (primitive) {
          let newCursor = primitive(globalCursor, getRef);

          if (newCursor === 'NEXT_BLOCK') {
            const currentIdx = blocks.findIndex(b => b.id === globalCursor.blockId);
            if (currentIdx < blocks.length - 1) {
              const nextBlock = blocks[currentIdx + 1];
              newCursor = { blockId: nextBlock.id, line: 0, col: 0 };
            } else {
              newCursor = null;
            }
          } else if (newCursor === 'PREV_BLOCK') {
            const currentIdx = blocks.findIndex(b => b.id === globalCursor.blockId);
            if (currentIdx > 0) {
              const prevBlock = blocks[currentIdx - 1];
              const prevData = blockDataRef.current[prevBlock.id];
              if (prevData) {
                const lastLine = prevData.lines.length - 1;
                newCursor = {
                  blockId: prevBlock.id,
                  line: lastLine,
                  col: prevData.lines[lastLine]?.length || 0
                };
              }
            } else {
              newCursor = null;
            }
          }

          if (newCursor) {
            setGlobalCursor(newCursor);
          }
        }
      }

      setAwaitingWindowCmd(false);
      return;
    }

    if (awaitingChar) {
      const count = pendingCount || 1;
      const primitive = navigationPrimitives[awaitingChar];

      if (primitive) {
        const getRef = (blockId) => blockDataRef.current[blockId];
        let newCursor = primitive(globalCursor, getRef, key, count);

        if (newCursor && newCursor !== 'NEXT_BLOCK' && newCursor !== 'PREV_BLOCK') {
          setGlobalCursor(newCursor);
        }
      }

      setAwaitingChar(null);
      setPendingCount(null);
      return;
    }

    if (!ctrlKey && /^[0-9]$/.test(key)) {
      const digit = parseInt(key, 10);
      setPendingCount((prev) => (prev || 0) * 10 + digit);
      return;
    }

    const keymapKey = ctrlKey ? `ctrl+${key.toLowerCase()}` : key;
    const count = pendingCount || 1;

    executeCommand(keymapKey, count);
    setPendingCount(null);
  }, [awaitingWindowCmd, awaitingChar, pendingCount, executeCommand, globalCursor, blocks, navigationPrimitives]);

  // Keyboard event listener
  useEffect(() => {
    const handleKeyDown = (e) => {
      const key = e.key;

      // Don't hijack keys while typing in an input (search box, forms, etc.).
      const ae = document.activeElement;
      if (
        ae &&
        (ae.tagName === 'INPUT' ||
          ae.tagName === 'TEXTAREA' ||
          ae.tagName === 'SELECT' ||
          ae.isContentEditable)
      ) {
        return;
      }

      if (key === 'Escape') {
        setPendingCount(null);
        setAwaitingChar(null);
        setAwaitingWindowCmd(false);
        return;
      }

      if (awaitingWindowCmd) {
        if (windowCommandMap.hasOwnProperty(key)) {
          e.preventDefault();
          handleNavigation(key, e.ctrlKey);
        }
        return;
      }

      if (awaitingChar) {
        e.preventDefault();
        handleNavigation(key, e.ctrlKey);
        return;
      }

      if (/^[0-9]$/.test(key)) {
        e.preventDefault();
        handleNavigation(key, e.ctrlKey);
        return;
      }

      const keymapKey = e.ctrlKey ? `ctrl+${key.toLowerCase()}` : key;
      const isHandled = keymap.hasOwnProperty(keymapKey);

      if (isHandled) {
        e.preventDefault();
        handleNavigation(key, e.ctrlKey);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleNavigation, awaitingChar, awaitingWindowCmd, keymap]);

  // In large-block mode we render nothing (no WebGL canvas/trail); the block
  // highlight is handled by the classList effect above.
  // The WebGL trail was removed (too gimmicky). Index/listing pages show only
  // the block highlight; elsewhere, the per-character terminal cursor.
  if (disableTrail || !charCursor) {
    return null;
  }

  return (
    <div
      className="vim-char-cursor"
      style={{
        left: `${charCursor.left}px`,
        top: `${charCursor.top}px`,
        width: `${charCursor.width}px`,
        height: `${charCursor.height}px`,
      }}
    />
  );
}

// Characters-per-line the element actually renders. Body text is monospace, so
// this makes wrapText's logical lines match the DOM's visual lines. (Headings
// are Fira Sans / proportional, but they're block-level — never cursor-level —
// and usually one line, so an approximate value is fine.)
function computeMaxCharsPerLine(element) {
  try {
    const cs = window.getComputedStyle(element);
    const padL = parseFloat(cs.paddingLeft) || 0;
    const padR = parseFloat(cs.paddingRight) || 0;
    // ~1rem of extra left padding appears when the block is the active cursor
    // block; subtract it so the wrap matches the active (cursor-visible) state.
    const activeShift = 16;
    const width = element.clientWidth - padL - padR - activeShift;
    const canvas =
      computeMaxCharsPerLine._canvas ||
      (computeMaxCharsPerLine._canvas = document.createElement('canvas'));
    const ctx = canvas.getContext('2d');
    // The cursor only shows on the active block, which renders MONO (Fira Code)
    // under the experiment — so measure mono width regardless of the block's
    // resting (proportional) font, so the cached wrap matches the active state.
    ctx.font = `${cs.fontSize} "Fira Code", ui-monospace, monospace`;
    const charW = ctx.measureText('0').width || 9;
    return Math.max(20, Math.min(200, Math.floor(width / charW)));
  } catch (e) {
    return 80;
  }
}

// Map a logical (line, col) cursor back to a character index in the block's
// text. wrapText drops exactly one separator char (space or newline) per line
// break, so each prior line contributes its length + 1.
function charIndexFromCursor(blockData, line, col) {
  const lines = (blockData && blockData.lines) || [];
  let idx = 0;
  for (let i = 0; i < line && i < lines.length; i++) {
    idx += (lines[i] ? lines[i].length : 0) + 1;
  }
  return idx + col;
}

// Find the on-screen rect of the character at `charIndex` within `element`,
// walking its text nodes (so nested links/code/strong are handled).
function getCharRect(element, charIndex) {
  const full = element.textContent || '';
  const lead = full.length - full.trimStart().length; // block.text was trimmed
  const target = Math.max(0, charIndex + lead);
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null);
  let acc = 0;
  let node;
  while ((node = walker.nextNode())) {
    const len = node.textContent.length;
    if (acc + len > target) {
      const off = target - acc;
      try {
        const range = document.createRange();
        range.setStart(node, Math.min(off, len));
        range.setEnd(node, Math.min(off + 1, len));
        const rect = range.getBoundingClientRect();
        if (rect && (rect.width || rect.height)) return rect;
      } catch (e) {
        return null;
      }
      return null;
    }
    acc += len;
  }
  return null;
}
