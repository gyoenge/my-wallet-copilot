/** 세이비 캐릭터 로고 (assets/savy_character.png → fe/public). */
export default function TLogo({
  size = 56,
  radius = 16,
  glow = true,
  className = "",
}: {
  size?: number;
  radius?: number;
  glow?: boolean;
  className?: string;
}) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/savy_character.png"
      alt="세이비"
      style={{
        width: size,
        height: size,
        minWidth: size,
        borderRadius: radius,
        boxShadow: glow ? "0 8px 22px rgba(124,92,246,0.4)" : undefined,
      }}
      className={`block object-cover ${className}`}
    />
  );
}
