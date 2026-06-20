"use client";

import type { Dashboard as DashboardData } from "@/lib/types";

const won = (x: number) => Math.round(x).toLocaleString();

// 디자인의 카테고리 색상 팔레트.
const PALETTE = [
  "#a78bfa", "#60a5fa", "#fbbf24", "#f472b6", "#22d3ee",
  "#fb923c", "#34d399", "#f87171", "#2dd4bf", "#818cf8", "#c084fc",
];

const SCORE_COLOR: Record<string, string> = {
  양호: "#34d399",
  보통: "#60a5fa",
  주의: "#fbbf24",
  위험: "#f87171",
};

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-[20px] border border-white/[0.06] bg-[rgba(20,24,38,0.7)] px-6 py-[22px]">
      <div className="mb-5 text-[16px] font-bold">{title}</div>
      {children}
    </div>
  );
}

/** 실데이터로 conic-gradient 도넛 + 범례 */
function Donut({ cats }: { cats: DashboardData["categories"] }) {
  const total = cats.reduce((s, c) => s + c.합계, 0) || 1;
  let acc = 0;
  const stops = cats.map((c, i) => {
    const start = (acc / total) * 100;
    acc += c.합계;
    const end = (acc / total) * 100;
    return `${PALETTE[i % PALETTE.length]} ${start}% ${end}%`;
  });

  return (
    <div className="flex items-center gap-[22px]">
      <div className="relative h-[168px] w-[168px] flex-none">
        <div
          className="h-[168px] w-[168px] rounded-full"
          style={{
            background: `conic-gradient(${stops.join(", ")})`,
            WebkitMask: "radial-gradient(transparent 54%, #000 55%)",
            mask: "radial-gradient(transparent 54%, #000 55%)",
          }}
        />
      </div>
      <div className="grid flex-1 grid-cols-2 gap-x-3.5 gap-y-[7px] text-[12.5px]">
        {cats.map((c, i) => (
          <div key={c.category} className="flex items-center gap-[7px]">
            <span
              className="h-[9px] w-[9px] flex-none rounded-[3px]"
              style={{ background: PALETTE[i % PALETTE.length] }}
            />
            <span className="text-[#cfd5e8]">
              {c.category} {c.비중}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** 실데이터 막대 차트 (상승 애니메이션) */
function Bars({
  data,
  gradient,
  height = 168,
}: {
  data: { label: string; value: number }[];
  gradient: [string, string];
  height?: number;
}) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="flex items-end gap-2.5" style={{ height }}>
      {data.map((d, i) => (
        <div key={d.label} className="flex flex-1 flex-col items-center gap-2">
          <div
            className="w-full rounded-t-[5px]"
            style={{
              height: `${Math.max((d.value / max) * 100, 3)}%`,
              background: `linear-gradient(${gradient[0]}, ${gradient[1]})`,
              transformOrigin: "bottom",
              animation: `wcRise 0.55s ${i * 0.05}s ease both`,
            }}
            title={`${d.label}: ${won(d.value)}원`}
          />
          <span className="text-[11px] text-[#8b93ad]">{d.label}</span>
        </div>
      ))}
    </div>
  );
}

export default function Dashboard({ data }: { data: DashboardData }) {
  const s = data.summary;
  const scoreColor = SCORE_COLOR[data.health.label] ?? "#60a5fa";

  const stats = [
    { label: "총지출", value: won(s.총지출), unit: "원" },
    { label: "월평균", value: won(s.월평균), unit: "원" },
    { label: "거래건수", value: String(s.거래건수), unit: "건" },
    { label: "건당평균", value: won(s.건당평균), unit: "원" },
  ];

  return (
    <div className="flex flex-col gap-[22px]">
      {/* 진단 히어로 */}
      <div
        className="rounded-[22px] border border-[rgba(139,124,246,0.22)] px-7 py-[26px]"
        style={{ background: "linear-gradient(150deg, rgba(48,38,92,0.85), rgba(26,28,52,0.85))" }}
      >
        <div className="mb-5 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#8b7cf6] to-[#5b8def] text-[16px] font-extrabold text-white">
              T
            </div>
            <div className="text-[17px] font-bold">김티의 한 줄 진단</div>
          </div>
          <div className="text-right">
            <div className="mb-1 text-xs text-[#9aa3bd]">소비 건강 점수</div>
            <div className="text-[22px] font-extrabold" style={{ color: scoreColor }}>
              {data.health.score}{" "}
              <span className="text-[14px] font-semibold text-[#9aa3bd]">
                {data.health.label}
              </span>
            </div>
          </div>
        </div>
        <ul className="m-0 flex list-none flex-col gap-[13px] p-0">
          {data.insights.map((t, i) => (
            <li key={i} className="flex gap-[11px] text-[15px] leading-[1.5] text-[#d7dcec]">
              <span className="text-[#8b7cf6]">•</span>
              <span>{t}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* 통계 4칸 */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {stats.map((m) => (
          <div
            key={m.label}
            className="rounded-[18px] border border-white/[0.06] bg-[rgba(20,24,38,0.7)] px-5 py-[18px]"
          >
            <div className="mb-2 text-[13px] text-[#9aa3bd]">{m.label}</div>
            <div className="text-[23px] font-extrabold tracking-tight">
              {m.value}
              <span className="text-[15px] font-bold">{m.unit}</span>
            </div>
          </div>
        ))}
      </div>

      {/* 차트 1행: 도넛 + 월별 */}
      <div className="grid gap-[22px] md:grid-cols-2">
        <Panel title="카테고리별 지출">
          <Donut cats={data.categories} />
        </Panel>
        <Panel title="월별 지출 추이">
          <Bars
            data={data.monthly.map((m) => ({ label: m.year_month, value: m.합계 }))}
            gradient={["#7db3ff", "#5b9bf6"]}
            height={188}
          />
        </Panel>
      </div>

      {/* 차트 2행: 요일 + 시간대 */}
      <div className="grid gap-[22px] md:grid-cols-2">
        <Panel title="요일별 지출">
          <Bars
            data={data.weekday.map((w) => ({ label: w.요일, value: w.합계 }))}
            gradient={["#b9a7ff", "#9275f0"]}
          />
        </Panel>
        <Panel title="시간대별 지출">
          <Bars
            data={data.timeBucket.map((t) => ({ label: t.시간대, value: t.합계 }))}
            gradient={["#5ee9b5", "#2bb98a"]}
          />
        </Panel>
      </div>
    </div>
  );
}
