"use client";

import { useState } from "react";

export default function Avatar({
  size = 48,
  variant = "face",
}: {
  size?: number;
  variant?: "face" | "main";
}) {
  const [ok, setOk] = useState(true);
  const src = variant === "face" ? "/kim-t-face.png" : "/kim-t-avatar.png";

  if (!ok) {
    return (
      <div
        className="flex items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-blue-500"
        style={{ width: size, height: size, fontSize: size * 0.5 }}
      >
        😏
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt="김티"
      onError={() => setOk(false)}
      className="rounded-2xl object-cover ring-1 ring-white/10"
      style={{ width: size, height: size }}
    />
  );
}
