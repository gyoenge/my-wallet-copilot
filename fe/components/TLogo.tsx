/** 김티(T) 로고 — 디자인의 보라/블루 그라데이션 사각형 "T". */
export default function TLogo({
  size = 56,
  font = 22,
  radius = 16,
  glow = true,
}: {
  size?: number;
  font?: number;
  radius?: number;
  glow?: boolean;
}) {
  return (
    <div
      style={{
        width: size,
        height: size,
        minWidth: size,
        fontSize: font,
        borderRadius: radius,
        boxShadow: glow ? "0 8px 22px rgba(124,92,246,0.4)" : undefined,
      }}
      className="flex items-center justify-center font-extrabold text-white bg-gradient-to-br from-[#8b7cf6] to-[#5b8def]"
    >
      T
    </div>
  );
}
