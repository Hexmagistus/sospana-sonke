"use client";

import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { CanvasTexture, MeshStandardMaterial, SRGBColorSpace, type Mesh } from "three";

function earthMaterial(): MeshStandardMaterial {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");
  const material = new MeshStandardMaterial({ color: "#16324f", metalness: 0.18, roughness: 0.48 });
  if (!ctx) return material;
  const ocean = ctx.createLinearGradient(0, 0, 0, 256);
  ocean.addColorStop(0, "#9ad8f0");
  ocean.addColorStop(0.45, "#1d6a90");
  ocean.addColorStop(1, "#0d3a56");
  ctx.fillStyle = ocean;
  ctx.fillRect(0, 0, 512, 256);
  ctx.fillStyle = "#1f8f7a";
  ctx.beginPath();
  ctx.ellipse(286, 132, 30, 54, 0.2, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.ellipse(270, 78, 18, 14, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#146b5c";
  ctx.fillRect(0, 118, 512, 10);
  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  texture.needsUpdate = true;
  material.map = texture;
  return material;
}

function Globe() {
  const ref = useRef<Mesh>(null);
  const material = useMemo(() => earthMaterial(), []);
  useEffect(() => {
    return () => {
      material.map?.dispose();
      material.dispose();
    };
  }, [material]);
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.22;
  });
  return (
    <mesh ref={ref} material={material}>
      <sphereGeometry args={[1.05, 40, 28]} />
    </mesh>
  );
}

export function ShowpieceCanvas() {
  return (
    <Canvas
      className="ss-showpiece-canvas"
      dpr={[1, 1.25]}
      camera={{ position: [0, 0.1, 3.15], fov: 35 }}
      gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}
    >
      <ambientLight intensity={0.55} />
      <directionalLight position={[3.2, 2.2, 4]} intensity={1.55} color="#fff6ea" />
      <directionalLight position={[-2.4, -0.6, -1.5]} intensity={0.35} color="#5eead4" />
      <Globe />
      <mesh rotation={[Math.PI / 2.15, 0.4, 0.2]}>
        <torusGeometry args={[1.42, 0.012, 8, 64]} />
        <meshStandardMaterial color="#5eead4" metalness={0.45} roughness={0.28} emissive="#0f766e" emissiveIntensity={0.25} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.28, 0]}>
        <circleGeometry args={[0.62, 28]} />
        <meshBasicMaterial color="#04101f" transparent opacity={0.35} />
      </mesh>
    </Canvas>
  );
}
