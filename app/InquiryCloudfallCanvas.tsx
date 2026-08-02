"use client";

import { useEffect, useRef } from "react";

type CloudfallLayer = "back" | "front";

const vertexShaderSource = `
attribute vec2 a_position;
varying vec2 v_uv;

void main() {
  v_uv = vec2(a_position.x * .5 + .5, .5 - a_position.y * .5);
  gl_Position = vec4(a_position, 0.0, 1.0);
}
`;

const fragmentShaderSource = `
precision highp float;

uniform vec2 u_resolution;
uniform float u_time;
uniform float u_layer;
varying vec2 v_uv;

float hash21(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

float valueNoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(hash21(i), hash21(i + vec2(1.0, 0.0)), f.x),
    mix(hash21(i + vec2(0.0, 1.0)), hash21(i + vec2(1.0, 1.0)), f.x),
    f.y
  );
}

float fbm(vec2 p) {
  float sum = 0.0;
  float amplitude = .54;
  mat2 turn = mat2(.80, -.60, .60, .80);
  for (int octave = 0; octave < 5; octave++) {
    sum += amplitude * valueNoise(p);
    p = turn * p * 2.03 + 17.17;
    amplitude *= .50;
  }
  return sum;
}

float segmentDistance(vec2 p, vec2 a, vec2 b) {
  vec2 pa = p - a;
  vec2 ba = b - a;
  float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
  return length(pa - ba * h);
}

float segmentProgress(vec2 p, vec2 a, vec2 b) {
  vec2 ba = b - a;
  return clamp(dot(p - a, ba) / dot(ba, ba), 0.0, 1.0);
}

float softTrail(vec2 p, vec2 a, vec2 b, float innerWidth, float outerWidth) {
  return 1.0 - smoothstep(innerWidth, outerWidth, segmentDistance(p, a, b));
}

float ellipse(vec2 p, vec2 center, vec2 radius) {
  float distanceFromCenter = length((p - center) / radius);
  return 1.0 - smoothstep(.72, 1.08, distanceFromCenter);
}

vec2 quadraticPoint(vec2 a, vec2 b, vec2 c, float t) {
  float inverse = 1.0 - t;
  return inverse * inverse * a + 2.0 * inverse * t * b + t * t * c;
}

float cloudDetail(vec2 p, vec2 velocity, float time, float scale) {
  vec2 moving = p * scale - velocity * time;
  vec2 warp = vec2(
    fbm(moving * .53 + vec2(2.7, 7.9)),
    fbm(moving * .47 + vec2(9.2, 1.4))
  );
  return fbm(moving + (warp - .5) * 1.85);
}

void main() {
  vec2 uv = v_uv;
  float aspect = u_resolution.x / max(u_resolution.y, 1.0);
  vec2 metric = vec2(uv.x * aspect, uv.y);
  float time = u_time;
  float shape = 0.0;
  float detail = 0.0;
  float opacity = 0.0;

  if (u_layer < .5) {
    // Windward reservoir and crest flow: a broad field approaches from the upper left,
    // narrows at the summit, and remains behind the mountain ink layer.
    vec2 a = vec2(.02 * aspect, .285);
    vec2 b = vec2(.60 * aspect, .315);
    vec2 c = vec2(.665 * aspect, .355);
    float reservoir = ellipse(metric, vec2(.30 * aspect, .31), vec2(.39 * aspect, .19));
    float upperCurrent = softTrail(metric, a, b, .065, .180);
    float crestCurrent = softTrail(metric, b, c, .035, .110);
    shape = max(reservoir * .82, max(upperCurrent, crestCurrent));
    float lowerBreak = smoothstep(.51, .33, uv.y);
    shape *= mix(.62, 1.0, lowerBreak);
    // The upper cloud sea moves only a little more than the pine: texture rolls
    // inside a fixed spatial mask, while every mountain pixel stays still.
    detail = cloudDetail(metric, vec2(.015 * aspect, .0018), time, 5.4);
    float slowSwell = cloudDetail(metric + vec2(.0, .14), vec2(.0075 * aspect, -.0012), time, 2.65);
    detail = mix(detail, slowSwell, .48);
    // Keep a translucent continuous body, then let the warped noise articulate
    // rolling crests inside it. This avoids disconnected white "spots".
    float rollingBody = mix(.30, 1.0, smoothstep(.20, .72, detail));
    float lateralFlow = .5 + .5 * sin(uv.x * 17.0 - time * .12 + (slowSwell - .5) * 2.8);
    rollingBody *= mix(.86, 1.08, smoothstep(.24, .82, lateralFlow));
    opacity = shape * rollingBody * .38;
  } else {
    // Leeward fall: the summit divides the cloud into one broad curtain and one
    // narrow ravine stream. Each branch has its own speed and dissolves downhill.
    vec2 p1 = vec2(.575 * aspect, .315);
    vec2 p2 = vec2(.525 * aspect, .475);
    vec2 p3 = vec2(.465 * aspect, .790);
    vec2 q1 = vec2(.715 * aspect, .365);
    vec2 q2 = vec2(.755 * aspect, .545);
    vec2 q3 = vec2(.785 * aspect, .795);
    float broadUpper = softTrail(metric, p1, p2, .045, .135);
    float broadLower = softTrail(metric, p2, p3, .055, .175);
    float narrowUpper = softTrail(metric, q1, q2, .022, .070);
    float narrowLower = softTrail(metric, q2, q3, .027, .090);
    float broad = max(broadUpper, broadLower);
    float narrow = max(narrowUpper, narrowLower);
    float valleyWisp = softTrail(
      metric,
      vec2(.53 * aspect, .69),
      vec2(.82 * aspect, .78),
      .018,
      .075
    );
    float downhillFade = 1.0 - smoothstep(.71, .91, uv.y);
    shape = max(broad, max(narrow * .92, valleyWisp * .58)) * downhillFade;

    float broadDetail = cloudDetail(metric, vec2(.006 * aspect, .052), time, 7.0);
    float narrowDetail = cloudDetail(metric + vec2(3.1, .0), vec2(.004 * aspect, .070), time, 8.7);
    float branchMix = smoothstep(.64, .76, uv.x);
    detail = mix(broadDetail, narrowDetail, branchMix);
    float billow = cloudDetail(metric + vec2(.0, time * .012), vec2(.010 * aspect, .040), time, 3.5);
    detail = mix(detail, billow, .30);

    float broadProgressUpper = segmentProgress(metric, p1, p2) * .38;
    float broadProgressLower = .38 + segmentProgress(metric, p2, p3) * .62;
    float broadProgress = (
      broadProgressUpper * broadUpper + broadProgressLower * broadLower
    ) / max(broadUpper + broadLower, .001);
    float narrowProgressUpper = segmentProgress(metric, q1, q2) * .42;
    float narrowProgressLower = .42 + segmentProgress(metric, q2, q3) * .58;
    float narrowProgress = (
      narrowProgressUpper * narrowUpper + narrowProgressLower * narrowLower
    ) / max(narrowUpper + narrowLower, .001);
    float flowProgress = mix(broadProgress, narrowProgress, branchMix);
    // Soft cloud bodies actually travel from the summit down two separate
    // leeward routes. The mountain image itself never moves; only these pale,
    // semi-transparent vapour bodies advance along the fixed paths.
    float cascadeFlow = 0.0;
    float cascadeRidges = 0.0;
    for (int cloudIndex = 0; cloudIndex < 7; cloudIndex++) {
      float index = float(cloudIndex);
      float progress = fract(time * .044 + index / 7.0);
      vec2 center = quadraticPoint(p1, p2, p3, progress);
      center.x += sin(index * 5.37 + time * .22) * .010 * aspect;
      center.y += cos(index * 3.71 + time * .18) * .006;
      float life = smoothstep(.02, .17, progress) * (1.0 - smoothstep(.78, .99, progress));
      vec2 radius = vec2((.056 + progress * .030) * aspect, .046 + progress * .036);
      float body = ellipse(metric, center, radius);
      float brokenEdge = mix(.76, 1.06, cloudDetail(metric + index, vec2(.0, .018), time, 9.2));
      cascadeFlow = max(cascadeFlow, body * brokenEdge * life);
    }
    for (int cloudIndex = 0; cloudIndex < 6; cloudIndex++) {
      float index = float(cloudIndex);
      float progress = fract(time * .052 + index / 6.0 + .13);
      vec2 center = quadraticPoint(q1, q2, q3, progress);
      center.x += sin(index * 4.13 + time * .19) * .006 * aspect;
      float life = smoothstep(.03, .20, progress) * (1.0 - smoothstep(.76, .98, progress));
      vec2 radius = vec2((.028 + progress * .018) * aspect, .034 + progress * .028);
      float body = ellipse(metric, center, radius);
      cascadeRidges = max(cascadeRidges, body * life);
    }
    // A faint continuous veil joins the travelling bodies into a single flow;
    // it is deliberately light so changing opacity reads as cloud, not moving rock.
    float advectedBillow = smoothstep(.31, .71, cloudDetail(
      metric,
      vec2(.003 * aspect, .105),
      time,
      6.2
    ));
    float fallingBody = mix(.14, .80, advectedBillow);
    float travellingBodies = max(cascadeFlow, cascadeRidges * .92);
    float fineRidges = smoothstep(.52, .78, cloudDetail(
      metric,
      vec2(.002 * aspect, .040),
      time,
      7.8
    ));
    opacity = shape * fallingBody;
    opacity += travellingBodies * mix(.18, .30, fineRidges);
    opacity *= downhillFade;
    opacity *= .58;
  }

  float feather = smoothstep(.0, .055, uv.x) * (1.0 - smoothstep(.945, 1.0, uv.x));
  feather *= smoothstep(.0, .045, uv.y) * (1.0 - smoothstep(.94, 1.0, uv.y));
  opacity *= feather;
  // Keep every animated pixel pale. Dark moving texture can be mistaken for
  // shifting mountain ink, while a warm-white veil clearly reads as vapour.
  vec3 cloudShadow = vec3(.885, .852, .790);
  vec3 cloudLight = vec3(.955, .925, .865);
  vec3 cloudColor = mix(cloudShadow, cloudLight, smoothstep(.24, .70, detail));
  gl_FragColor = vec4(cloudColor * opacity, opacity);
}
`;

function compileShader(gl: WebGLRenderingContext, type: number, source: string) {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    console.error("Inquiry cloudfall shader failed to compile", gl.getShaderInfoLog(shader));
    gl.deleteShader(shader);
    return null;
  }
  return shader;
}

export function InquiryCloudfallCanvas({ layer }: { layer: CloudfallLayer }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const gl = canvas.getContext("webgl", {
      alpha: true,
      antialias: false,
      depth: false,
      premultipliedAlpha: true,
      preserveDrawingBuffer: false,
      powerPreference: "low-power",
    });
    if (!gl) return;

    const vertexShader = compileShader(gl, gl.VERTEX_SHADER, vertexShaderSource);
    const fragmentShader = compileShader(gl, gl.FRAGMENT_SHADER, fragmentShaderSource);
    if (!vertexShader || !fragmentShader) return;

    const program = gl.createProgram();
    if (!program) return;
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error("Inquiry cloudfall program failed to link", gl.getProgramInfoLog(program));
      gl.deleteProgram(program);
      return;
    }

    const buffer = gl.createBuffer();
    const positionLocation = gl.getAttribLocation(program, "a_position");
    const resolutionLocation = gl.getUniformLocation(program, "u_resolution");
    const timeLocation = gl.getUniformLocation(program, "u_time");
    const layerLocation = gl.getUniformLocation(program, "u_layer");
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]),
      gl.STATIC_DRAW,
    );
    gl.useProgram(program);
    gl.enableVertexAttribArray(positionLocation);
    gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);
    gl.uniform1f(layerLocation, layer === "front" ? 1 : 0);
    gl.clearColor(0, 0, 0, 0);

    let frame = 0;
    let visible = true;
    const startedAt = performance.now();
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
      const width = Math.max(1, Math.round(canvas.clientWidth * ratio));
      const height = Math.max(1, Math.round(canvas.clientHeight * ratio));
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
        gl.viewport(0, 0, width, height);
      }
    };

    const draw = (now: number) => {
      resize();
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.uniform2f(resolutionLocation, canvas.width, canvas.height);
      gl.uniform1f(timeLocation, reducedMotion ? 4.0 : (now - startedAt) / 1000);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      if (!reducedMotion && visible) frame = window.requestAnimationFrame(draw);
    };

    const observer = new IntersectionObserver(([entry]) => {
      const nextVisible = entry.isIntersecting;
      if (nextVisible && !visible && !reducedMotion) {
        visible = true;
        frame = window.requestAnimationFrame(draw);
      } else if (!nextVisible && visible) {
        visible = false;
        window.cancelAnimationFrame(frame);
      }
    }, { threshold: .02 });
    observer.observe(canvas);
    frame = window.requestAnimationFrame(draw);

    return () => {
      observer.disconnect();
      window.cancelAnimationFrame(frame);
      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
      gl.deleteShader(vertexShader);
      gl.deleteShader(fragmentShader);
    };
  }, [layer]);

  return <canvas ref={canvasRef} className={`inquiry-cloudfall-canvas inquiry-cloudfall-canvas-${layer}`} />;
}
