"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./page.module.css";

type RiverFlowCanvasProps = {
  active: boolean;
};

const vertexShaderSource = [
  "attribute vec2 a_position;",
  "varying vec2 v_uv;",
  "void main() {",
  "  v_uv = a_position * 0.5 + 0.5;",
  "  gl_Position = vec4(a_position, 0.0, 1.0);",
  "}",
].join("\n");

const fragmentShaderSource = [
  "precision mediump float;",
  "varying vec2 v_uv;",
  "uniform sampler2D u_scene;",
  "uniform sampler2D u_motion_mask;",
  "uniform vec2 u_resolution;",
  "uniform vec2 u_texture_size;",
  "uniform float u_time;",
  "",
  "float hash(vec2 p) {",
  "  p = fract(p * vec2(123.34, 456.21));",
  "  p += dot(p, p + 45.32);",
  "  return fract(p.x * p.y);",
  "}",
  "",
  "float noise(vec2 p) {",
  "  vec2 cell = floor(p);",
  "  vec2 local = fract(p);",
  "  local = local * local * (3.0 - 2.0 * local);",
  "  return mix(",
  "    mix(hash(cell), hash(cell + vec2(1.0, 0.0)), local.x),",
  "    mix(hash(cell + vec2(0.0, 1.0)), hash(cell + vec2(1.0, 1.0)), local.x),",
  "    local.y",
  "  );",
  "}",
  "",
  "float fbm(vec2 p) {",
  "  float value = 0.0;",
  "  float weight = 0.55;",
  "  for (int octave = 0; octave < 4; octave++) {",
  "    value += weight * noise(p);",
  "    p = p * 2.03 + vec2(8.1, 3.7);",
  "    weight *= 0.48;",
  "  }",
  "  return value;",
  "}",
  "",
  "float pathMix(float y, float y0, float y1, float a, float b) {",
  "  return mix(a, b, smoothstep(y0, y1, y));",
  "}",
  "",
  "float riverCenter(float y) {",
  "  if (y < 0.18) return pathMix(y, 0.10, 0.18, 0.515, 0.480);",
  "  if (y < 0.24) return pathMix(y, 0.18, 0.24, 0.480, 0.520);",
  "  if (y < 0.30) return pathMix(y, 0.24, 0.30, 0.520, 0.430);",
  "  if (y < 0.36) return pathMix(y, 0.30, 0.36, 0.430, 0.325);",
  "  if (y < 0.42) return pathMix(y, 0.36, 0.42, 0.325, 0.360);",
  "  if (y < 0.49) return pathMix(y, 0.42, 0.49, 0.360, 0.580);",
  "  if (y < 0.54) return pathMix(y, 0.49, 0.54, 0.580, 0.530);",
  "  if (y < 0.61) return pathMix(y, 0.54, 0.61, 0.530, 0.340);",
  "  if (y < 0.67) return pathMix(y, 0.61, 0.67, 0.340, 0.350);",
  "  if (y < 0.74) return pathMix(y, 0.67, 0.74, 0.350, 0.560);",
  "  if (y < 0.80) return pathMix(y, 0.74, 0.80, 0.560, 0.585);",
  "  if (y < 0.86) return pathMix(y, 0.80, 0.86, 0.585, 0.430);",
  "  if (y < 0.92) return pathMix(y, 0.86, 0.92, 0.430, 0.500);",
  "  return pathMix(y, 0.92, 1.00, 0.500, 0.540);",
  "}",
  "",
  "float riverLeft(float y) {",
  "  if (y < 0.18) return pathMix(y, 0.10, 0.18, 0.480, 0.440);",
  "  if (y < 0.24) return pathMix(y, 0.18, 0.24, 0.440, 0.380);",
  "  if (y < 0.30) return pathMix(y, 0.24, 0.30, 0.380, 0.280);",
  "  if (y < 0.36) return pathMix(y, 0.30, 0.36, 0.280, 0.180);",
  "  if (y < 0.42) return pathMix(y, 0.36, 0.42, 0.180, 0.190);",
  "  if (y < 0.49) return pathMix(y, 0.42, 0.49, 0.190, 0.320);",
  "  if (y < 0.54) return pathMix(y, 0.49, 0.54, 0.320, 0.240);",
  "  if (y < 0.60) return pathMix(y, 0.54, 0.60, 0.240, 0.160);",
  "  if (y < 0.67) return pathMix(y, 0.60, 0.67, 0.160, 0.120);",
  "  if (y < 0.74) return pathMix(y, 0.67, 0.74, 0.120, 0.140);",
  "  if (y < 0.80) return pathMix(y, 0.74, 0.80, 0.140, 0.080);",
  "  if (y < 0.86) return pathMix(y, 0.80, 0.86, 0.080, 0.030);",
  "  if (y < 0.92) return pathMix(y, 0.86, 0.92, 0.030, 0.000);",
  "  return pathMix(y, 0.92, 1.00, 0.000, 0.000);",
  "}",
  "",
  "float riverRight(float y) {",
  "  if (y < 0.18) return pathMix(y, 0.10, 0.18, 0.550, 0.560);",
  "  if (y < 0.24) return pathMix(y, 0.18, 0.24, 0.560, 0.650);",
  "  if (y < 0.30) return pathMix(y, 0.24, 0.30, 0.650, 0.620);",
  "  if (y < 0.36) return pathMix(y, 0.30, 0.36, 0.620, 0.520);",
  "  if (y < 0.42) return pathMix(y, 0.36, 0.42, 0.520, 0.670);",
  "  if (y < 0.49) return pathMix(y, 0.42, 0.49, 0.670, 0.760);",
  "  if (y < 0.54) return pathMix(y, 0.49, 0.54, 0.760, 0.650);",
  "  if (y < 0.60) return pathMix(y, 0.54, 0.60, 0.650, 0.520);",
  "  if (y < 0.67) return pathMix(y, 0.60, 0.67, 0.520, 0.630);",
  "  if (y < 0.74) return pathMix(y, 0.67, 0.74, 0.630, 0.860);",
  "  if (y < 0.80) return pathMix(y, 0.74, 0.80, 0.860, 0.940);",
  "  if (y < 0.86) return pathMix(y, 0.80, 0.86, 0.940, 0.980);",
  "  if (y < 0.92) return pathMix(y, 0.86, 0.92, 0.980, 1.000);",
  "  return pathMix(y, 0.92, 1.00, 1.000, 1.000);",
  "}",
  "",
  "vec2 coverUv(vec2 screenUv) {",
  "  float viewportAspect = u_resolution.x / max(u_resolution.y, 1.0);",
  "  float textureAspect = u_texture_size.x / max(u_texture_size.y, 1.0);",
  "  vec2 result = screenUv;",
  "  if (viewportAspect > textureAspect) {",
  "    float visibleHeight = textureAspect / viewportAspect;",
  "    result.y = 0.5 + (screenUv.y - 0.5) * visibleHeight;",
  "  } else {",
  "    float visibleWidth = viewportAspect / textureAspect;",
  "    result.x = 0.5 + (screenUv.x - 0.5) * visibleWidth;",
  "  }",
  "  return result;",
  "}",
  "",
  "float luma(vec3 color) {",
  "  return dot(color, vec3(0.299, 0.587, 0.114));",
  "}",
  "",
  "void main() {",
  "  vec2 screen = vec2(v_uv.x, 1.0 - v_uv.y);",
  "  float center = riverCenter(screen.y);",
  "  float depth = smoothstep(0.18, 1.0, screen.y);",
  "  float leftBank = riverLeft(screen.y);",
  "  float rightBank = riverRight(screen.y);",
  "  float bankCenter = (leftBank + rightBank) * 0.5;",
  "  float width = max((rightBank - leftBank) * 0.5, 0.001);",
  "  float lane = (screen.x - bankCenter) / width;",
  "  float edgeSoftness = mix(0.030, 0.095, pow(depth, 1.08));",
  "  float bankFade = smoothstep(leftBank, leftBank + edgeSoftness, screen.x)",
  "    * (1.0 - smoothstep(rightBank - edgeSoftness, rightBank, screen.x));",
  "  float sourceFade = smoothstep(0.13, 0.27, screen.y);",
  "  float river = bankFade * sourceFade;",
  "  vec2 sceneUv = coverUv(v_uv);",
  "  vec3 baseColor = texture2D(u_scene, sceneUv).rgb;",
  "  float authoredWater = texture2D(u_motion_mask, sceneUv).r;",
  "",
  "  float epsilon = 0.007;",
  "  float nextCenter = riverCenter(min(screen.y + epsilon, 1.0));",
  "  float previousCenter = riverCenter(max(screen.y - epsilon, 0.0));",
  "  float slope = (nextCenter - previousCenter) / (2.0 * epsilon);",
  "  float farNext = riverCenter(min(screen.y + epsilon * 2.0, 1.0));",
  "  float farPrevious = riverCenter(max(screen.y - epsilon * 2.0, 0.0));",
  "  float nextSlope = (farNext - center) / (2.0 * epsilon);",
  "  float previousSlope = (center - farPrevious) / (2.0 * epsilon);",
  "  float curvature = clamp((nextSlope - previousSlope) * 0.82, -1.0, 1.0);",
  "",
  "  vec2 tangentScreen = normalize(vec2(slope, 1.0));",
  "  vec2 normalScreen = vec2(-tangentScreen.y, tangentScreen.x);",
  "  vec2 tangentUv = normalize(",
  "    coverUv(v_uv + vec2(tangentScreen.x, -tangentScreen.y) * 0.01) - sceneUv",
  "  );",
  "  vec2 normalUv = normalize(",
  "    coverUv(v_uv + vec2(normalScreen.x, -normalScreen.y) * 0.01) - sceneUv",
  "  );",
  "  float arc = screen.y + slope * (screen.x - center) / (1.0 + slope * slope);",
  "",
  "  float motionPresence = smoothstep(0.0, 0.55, u_time);",
  "  float flowTime = u_time * 1.62;",
  "  float phase = fract(flowTime * mix(0.075, 0.135, depth));",
  "  float secondPhase = fract(phase + 0.5);",
  "  float firstWeight = 1.0 - abs(phase * 2.0 - 1.0);",
  "  float travel = mix(0.012, 0.050, pow(depth, 1.18));",
  "",
  "  float broadWarp = fbm(vec2(arc * 6.4 - flowTime * 0.17, lane * 2.7 + 4.0)) - 0.5;",
  "  float smallWarp = fbm(vec2(lane * 5.1 - 8.0, arc * 10.5 - flowTime * 0.48)) - 0.5;",
  "  float bendStrength = abs(curvature) * smoothstep(0.24, 0.92, depth);",
  "  float outsideBank = smoothstep(0.08, 0.76, lane * sign(curvature));",
  "  float collision = bendStrength * outsideBank * bankFade;",
  "  float collisionBreak = fbm(vec2(arc * 13.0 - flowTime * 0.86, lane * 5.8 + curvature * 3.0));",
  "  float crossShift = broadWarp * 0.010 * depth",
  "    + curvature * collision * (0.007 + collisionBreak * 0.007);",
  "  float alongJitter = smallWarp * 0.008 * depth;",
  "",
  "  vec2 firstOffset = tangentUv * (phase * travel + alongJitter)",
  "    + normalUv * crossShift;",
  "  vec2 secondOffset = tangentUv * (secondPhase * travel + alongJitter)",
  "    + normalUv * crossShift;",
  "  vec3 firstFlow = texture2D(u_scene, sceneUv - firstOffset).rgb;",
  "  vec3 secondFlow = texture2D(u_scene, sceneUv - secondOffset).rgb;",
  "  vec3 advected = mix(secondFlow, firstFlow, firstWeight);",
  "",
  "  vec2 flowStep = tangentUv * mix(0.0025, 0.0055, depth);",
  "  float aheadLuma = luma(texture2D(u_scene, sceneUv - firstOffset + flowStep).rgb);",
  "  float behindLuma = luma(texture2D(u_scene, sceneUv - firstOffset - flowStep).rgb);",
  "  float advectedLuma = luma(advected);",
  "  float foamEdge = smoothstep(0.025, 0.105, abs(aheadLuma - behindLuma));",
  "  vec2 foamCrossStep = normalUv * mix(0.0024, 0.0062, depth);",
  "  vec3 crossA = texture2D(u_scene, sceneUv - firstOffset + foamCrossStep).rgb;",
  "  vec3 crossB = texture2D(u_scene, sceneUv - firstOffset - foamCrossStep).rgb;",
  "  float crossFoamEdge = smoothstep(0.022, 0.095, abs(luma(crossA) - luma(crossB)));",
  "  float sourceFoam = smoothstep(0.57, 0.78, advectedLuma);",
  "  float foamBreak = smoothstep(0.46, 0.78, fbm(vec2(",
  "    lane * 11.0 + broadWarp * 2.0,",
  "    arc * 17.0 - flowTime * 1.28",
  "  )));",
  "  float bendFoam = collision * sourceFoam * foamBreak;",
  "  float brokenFoam = sourceFoam * foamEdge * mix(0.35, 1.0, foamBreak);",
  "  float sprayPulse = smoothstep(0.60, 0.86, fbm(vec2(",
  "    arc * 23.0 - flowTime * 2.05,",
  "    lane * 13.5 + curvature * 4.0",
  "  )));",
  "  float rapidDetail = sourceFoam * max(foamEdge, crossFoamEdge)",
  "    * sprayPulse * smoothstep(0.38, 0.94, depth);",
  "  vec3 crossFoamSource = mix(crossA, crossB, step(luma(crossA), luma(crossB)));",
  "  float thrownFoam = smoothstep(0.60, 0.82, luma(crossFoamSource))",
  "    * crossFoamEdge * sprayPulse * (0.22 + collision * 0.78);",
  "",
  "  vec3 warmFoam = vec3(0.978, 0.953, 0.895);",
  "  float undertowPattern = smoothstep(0.46, 0.78, fbm(vec2(",
  "    lane * 3.4 - arc * 4.0 + 6.0,",
  "    arc * 8.0 - flowTime * 0.56",
  "  )));",
  "  float undertow = undertowPattern * (1.0 - sourceFoam) * depth * 0.075;",
  "  vec3 waterColor = advected * (1.0 - undertow);",
  "  waterColor = mix(waterColor, max(waterColor, crossFoamSource), thrownFoam * 0.16);",
  "  float light = brokenFoam * 0.10 + bendFoam * 0.18",
  "    + rapidDetail * 0.075 + thrownFoam * 0.065;",
  "  waterColor = mix(waterColor, warmFoam, clamp(light, 0.0, 0.24));",
  "  float activeRiver = river * motionPresence * authoredWater;",
  "  gl_FragColor = vec4(mix(baseColor, waterColor, activeRiver), 1.0);",
  "}",
].join("\n");

function compileShader(
  gl: WebGLRenderingContext,
  type: number,
  source: string,
): WebGLShader | null {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (gl.getShaderParameter(shader, gl.COMPILE_STATUS)) return shader;
  gl.deleteShader(shader);
  return null;
}

export default function RiverFlowCanvas({ active }: RiverFlowCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!canvas) return;

    const gl = canvas.getContext("webgl", {
      alpha: false,
      antialias: false,
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
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return;

    const positionLocation = gl.getAttribLocation(program, "a_position");
    const resolutionLocation = gl.getUniformLocation(program, "u_resolution");
    const textureSizeLocation = gl.getUniformLocation(program, "u_texture_size");
    const timeLocation = gl.getUniformLocation(program, "u_time");
    const sceneLocation = gl.getUniformLocation(program, "u_scene");
    const motionMaskLocation = gl.getUniformLocation(program, "u_motion_mask");
    const buffer = gl.createBuffer();
    const texture = gl.createTexture();
    const motionMaskTexture = gl.createTexture();
    if (!buffer || !texture || !motionMaskTexture || positionLocation < 0) return;

    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]),
      gl.STATIC_DRAW,
    );
    gl.useProgram(program);
    gl.enableVertexAttribArray(positionLocation);
    gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, 1);
    gl.uniform1i(sceneLocation, 0);
    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, motionMaskTexture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.uniform1i(motionMaskLocation, 1);

    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 1.35);
      const width = Math.max(1, Math.round(bounds.width * pixelRatio));
      const height = Math.max(1, Math.round(bounds.height * pixelRatio));
      if (canvas.width === width && canvas.height === height) return;
      canvas.width = width;
      canvas.height = height;
      gl.viewport(0, 0, width, height);
    };

    let animationFrame = 0;
    let accumulatedTime = 0;
    let lastFrameAt = performance.now();
    let sceneReady = false;
    let motionMaskReady = false;

    const draw = (now: number) => {
      if (!sceneReady || !motionMaskReady) {
        animationFrame = window.requestAnimationFrame(draw);
        lastFrameAt = now;
        return;
      }
      if (active && !reduceMotion && !document.hidden) {
        accumulatedTime += Math.min((now - lastFrameAt) / 1000, 0.05);
      }
      lastFrameAt = now;
      resize();
      gl.useProgram(program);
      gl.uniform2f(resolutionLocation, canvas.width, canvas.height);
      gl.uniform1f(timeLocation, accumulatedTime);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      animationFrame = window.requestAnimationFrame(draw);
    };

    const image = new Image();
    image.onload = () => {
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
      gl.uniform2f(textureSizeLocation, image.naturalWidth, image.naturalHeight);
      sceneReady = true;
      if (motionMaskReady) setReady(true);
    };
    image.src = "/method-river-mobile-v2.webp";
    const motionMaskImage = new Image();
    motionMaskImage.onload = () => {
      gl.activeTexture(gl.TEXTURE1);
      gl.bindTexture(gl.TEXTURE_2D, motionMaskTexture);
      gl.texImage2D(
        gl.TEXTURE_2D,
        0,
        gl.RGBA,
        gl.RGBA,
        gl.UNSIGNED_BYTE,
        motionMaskImage,
      );
      motionMaskReady = true;
      if (sceneReady) setReady(true);
    };
    motionMaskImage.src = "/method-river-motion-mask-v1.png";
    animationFrame = window.requestAnimationFrame(draw);

    return () => {
      window.cancelAnimationFrame(animationFrame);
      image.onload = null;
      motionMaskImage.onload = null;
      gl.deleteTexture(texture);
      gl.deleteTexture(motionMaskTexture);
      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
      gl.deleteShader(vertexShader);
      gl.deleteShader(fragmentShader);
    };
  }, [active]);

  return (
    <canvas
      ref={canvasRef}
      className={styles.riverFlowCanvas + (ready ? " " + styles.riverFlowReady : "")}
      aria-hidden="true"
    />
  );
}
