/* neural-noise.js · vanilla WebGL animated background (ported from React component)
   Usage: <canvas id="neural"></canvas> then initNeuralNoise('#neural', {color,opacity,speed})
   Zero dependencies. Respects prefers-reduced-motion (renders one static frame). */
(function (global) {
  function initNeuralNoise(selector, opts = {}) {
    const canvas = typeof selector === 'string' ? document.querySelector(selector) : selector;
    if (!canvas) return;

    const color   = opts.color   || [0.45, 0.42, 0.95];
    const opacity  = opts.opacity ?? 0.9;
    const speed    = opts.speed   ?? 0.0009;
    const reduce   = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    canvas.style.opacity = opacity;

    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (!gl) { canvas.style.display = 'none'; return; }

    const pointer = { x: 0, y: 0, tX: 0, tY: 0 };
    let uniforms;

    const vsSource = `
      precision mediump float;
      varying vec2 vUv;
      attribute vec2 a_position;
      void main() { vUv = 0.5 * (a_position + 1.0); gl_Position = vec4(a_position, 0.0, 1.0); }`;

    const fsSource = `
      precision mediump float;
      varying vec2 vUv;
      uniform float u_time;
      uniform float u_ratio;
      uniform vec2 u_pointer_position;
      uniform vec3 u_color;
      uniform float u_speed;
      vec2 rotate(vec2 uv, float th) { return mat2(cos(th), sin(th), -sin(th), cos(th)) * uv; }
      float neuro_shape(vec2 uv, float t, float p) {
        vec2 sine_acc = vec2(0.0);
        vec2 res = vec2(0.0);
        float scale = 8.0;
        for (int j = 0; j < 15; j++) {
          uv = rotate(uv, 1.0);
          sine_acc = rotate(sine_acc, 1.0);
          vec2 layer = uv * scale + float(j) + sine_acc - t;
          sine_acc += sin(layer) + 2.4 * p;
          res += (0.5 + 0.5 * cos(layer)) / scale;
          scale *= 1.2;
        }
        return res.x + res.y;
      }
      void main() {
        vec2 uv = 0.5 * vUv;
        uv.x *= u_ratio;
        vec2 pointer = vUv - u_pointer_position;
        pointer.x *= u_ratio;
        float p = clamp(length(pointer), 0.0, 1.0);
        p = 0.5 * pow(1.0 - p, 2.0);
        float t = u_speed * u_time;
        vec3 col = vec3(0.0);
        float noise = neuro_shape(uv, t, p);
        noise = 1.2 * pow(noise, 3.0);
        noise += pow(noise, 10.0);
        noise = max(0.0, noise - 0.5);
        noise *= (1.0 - length(vUv - 0.5));
        col = u_color * noise;
        gl_FragColor = vec4(col, noise);
      }`;

    function createShader(src, type) {
      const s = gl.createShader(type);
      gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { console.error(gl.getShaderInfoLog(s)); gl.deleteShader(s); return null; }
      return s;
    }
    function createProgram(vs, fs) {
      const p = gl.createProgram();
      gl.attachShader(p, vs); gl.attachShader(p, fs); gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) { console.error(gl.getProgramInfoLog(p)); return null; }
      return p;
    }
    function getUniforms(program) {
      const u = {}, n = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS);
      for (let i = 0; i < n; i++) { const name = gl.getActiveUniform(program, i).name; u[name] = gl.getUniformLocation(program, name); }
      return u;
    }

    const vs = createShader(vsSource, gl.VERTEX_SHADER);
    const fs = createShader(fsSource, gl.FRAGMENT_SHADER);
    const program = createProgram(vs, fs);
    if (!program) { canvas.style.display = 'none'; return; }
    uniforms = getUniforms(program);

    const verts = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, verts, gl.STATIC_DRAW);
    gl.useProgram(program);
    const loc = gl.getAttribLocation(program, 'a_position');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

    gl.uniform3f(uniforms.u_color, color[0], color[1], color[2]);
    gl.uniform1f(uniforms.u_speed, speed);

    function resize() {
      const dpr = Math.min(window.devicePixelRatio, 2);
      canvas.width  = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      if (uniforms.u_ratio) gl.uniform1f(uniforms.u_ratio, canvas.width / canvas.height);
      gl.viewport(0, 0, canvas.width, canvas.height);
    }
    resize();
    window.addEventListener('resize', resize);

    const move = (x, y) => { pointer.tX = x; pointer.tY = y; };
    window.addEventListener('pointermove', e => move(e.clientX, e.clientY), { passive: true });
    window.addEventListener('touchmove', e => { if (e.targetTouches[0]) move(e.targetTouches[0].clientX, e.targetTouches[0].clientY); }, { passive: true });

    function render() {
      const t = performance.now();
      pointer.x += (pointer.tX - pointer.x) * 0.2;
      pointer.y += (pointer.tY - pointer.y) * 0.2;
      gl.uniform1f(uniforms.u_time, t);
      gl.uniform2f(uniforms.u_pointer_position, pointer.x / window.innerWidth, 1 - pointer.y / window.innerHeight);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      if (!reduce) requestAnimationFrame(render);
    }
    render();
  }

  global.initNeuralNoise = initNeuralNoise;
})(window);
