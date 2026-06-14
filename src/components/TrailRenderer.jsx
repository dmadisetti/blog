import React, { useEffect, useRef } from 'react';

export default function TrailRenderer({ trails, blocks, blockDataRef, currentCursor }) {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const glRef = useRef({ program: null, buffer: null, locations: {} });
  const trailColor = '#00ffff'; // Cyan

  // Initialize WebGL
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = canvas.getContext('webgl');
    if (!gl) return;

    const vertexShaderSource = `
      attribute vec2 position;
      void main() {
        gl_Position = vec4(position, 0.0, 1.0);
      }
    `;

    const fragmentShaderSource = `
      precision mediump float;
      uniform vec3 uColor;
      uniform float uAlpha;
      void main() {
        gl_FragColor = vec4(uColor, uAlpha);
      }
    `;

    function compileShader(source, type) {
      const shader = gl.createShader(type);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) return null;
      return shader;
    }

    const vertexShader = compileShader(vertexShaderSource, gl.VERTEX_SHADER);
    const fragmentShader = compileShader(fragmentShaderSource, gl.FRAGMENT_SHADER);
    const program = gl.createProgram();
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return;

    gl.useProgram(program);

    const buffer = gl.createBuffer();
    const positionLocation = gl.getAttribLocation(program, 'position');
    const uColorLocation = gl.getUniformLocation(program, 'uColor');
    const uAlphaLocation = gl.getUniformLocation(program, 'uAlpha');

    glRef.current = { program, buffer, locations: { positionLocation, uColorLocation, uAlphaLocation } };

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

    function render(time) {
      const displayWidth = canvas.clientWidth;
      const displayHeight = canvas.clientHeight;

      if (canvas.width !== displayWidth || canvas.height !== displayHeight) {
        canvas.width = displayWidth;
        canvas.height = displayHeight;
        gl.viewport(0, 0, canvas.width, canvas.height);
      }

      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);

      const r = parseInt(trailColor.slice(1, 3), 16) / 255;
      const g = parseInt(trailColor.slice(3, 5), 16) / 255;
      const b = parseInt(trailColor.slice(5, 7), 16) / 255;

      gl.uniform3f(glRef.current.locations.uColorLocation, r, g, b);

      // Render active trails
      trails.forEach(trail => {
        if (time < trail.endTime) {
          const elapsed = time - trail.startTime;
          const duration = trail.endTime - trail.startTime;
          const progress = Math.min(elapsed / duration, 1.0);

          const fadeStart = 0.7;
          const alpha = progress < fadeStart ? 0.8 : 0.8 * (1.0 - ((progress - fadeStart) / (1.0 - fadeStart)));

          gl.uniform1f(glRef.current.locations.uAlphaLocation, alpha);

          // Calculate positions for trail quad
          const fromPos = getCursorScreenPos(trail.from, blocks, blockDataRef.current);
          const toPos = getCursorScreenPos(trail.to, blocks, blockDataRef.current);

          if (fromPos && toPos) {
            const vertices = createTrailQuad(fromPos, toPos, canvas.width, canvas.height);

            gl.bindBuffer(gl.ARRAY_BUFFER, glRef.current.buffer);
            gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.DYNAMIC_DRAW);

            gl.enableVertexAttribArray(glRef.current.locations.positionLocation);
            gl.vertexAttribPointer(glRef.current.locations.positionLocation, 2, gl.FLOAT, false, 0, 0);

            gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
          }
        }
      });

      animationRef.current = requestAnimationFrame(render);
    }

    animationRef.current = requestAnimationFrame(render);

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [trails, blocks]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 9998,
        mixBlendMode: 'screen'
      }}
    />
  );
}

// Helper to get cursor position relative to canvas
function getCursorScreenPos(cursor, blocks, blockData) {
  const block = blocks.find(b => b.id === cursor.blockId);
  if (!block || !block.element) return null;

  // Get element position relative to its offset parent (content container)
  const rect = block.element.getBoundingClientRect();

  // Get canvas/container position
  const canvas = document.getElementById('vim-navigation-root');
  const containerRect = canvas ? canvas.getBoundingClientRect() : { left: 0, top: 0 };

  // Calculate position relative to container
  const x = rect.left - containerRect.left + (rect.width * 0.1); // 10% from left edge
  const y = rect.top - containerRect.top + (rect.height * 0.3); // 30% from top

  return { x, y };
}

// Create a quad for the trail
function createTrailQuad(from, to, canvasWidth, canvasHeight) {
  // Convert screen coordinates to WebGL normalized device coordinates (-1 to 1)
  const x1 = ((from.x / canvasWidth) * 2) - 1;
  const y1 = 1 - ((from.y / canvasHeight) * 2);
  const x2 = ((to.x / canvasWidth) * 2) - 1;
  const y2 = 1 - ((to.y / canvasHeight) * 2);

  // Create a thin quad between the two points
  const thickness = 0.01; // Trail thickness in NDC

  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.sqrt(dx * dx + dy * dy);

  if (len === 0) {
    // Same position, no trail
    return new Float32Array([x1, y1, x1, y1, x1, y1, x1, y1]);
  }

  const nx = -dy / len * thickness;
  const ny = dx / len * thickness;

  // Four corners of the quad
  return new Float32Array([
    x1 - nx, y1 - ny,  // Bottom-left
    x1 + nx, y1 + ny,  // Top-left
    x2 - nx, y2 - ny,  // Bottom-right
    x2 + nx, y2 + ny   // Top-right
  ]);
}
