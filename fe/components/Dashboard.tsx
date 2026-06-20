"use client";

import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Dashboard as DashboardData } from "@/lib/types";

const won = (x: number) => `${Math.round(x).toLocaleString()}원`;
const short = (x: number) =>
  x >= 10000 ? `${Math.round(x / 10000)}만` : `${Math.round(x / 1000)}천`;

const PALETTE = [
  "#A78BFA", "#60A5FA", "#34D399", "#FBBF24", "#F472B6",
  "#22D3EE", "#FB923C", "#A3E635", "#F87171", "#94A3B8", "#C084FC",
];

function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-3xl border border-white/10 bg-white/[0.03] p-5 shadow-2xl shadow-black/20 ${className}`}
    >
      {title && (
        <h3 className="mb-3 text-sm font-bold text-slate-300">{title}</h3>
      )}
      {children}
    </div>
  );
}

const tooltipStyle = {
  background: "#0E1422",
  border: "1px solid rgba(148,163,184,0.2)",
  borderRadius: 12,
  color: "#E5E7EB",
};

export default function Dashboard({ data }: { data: DashboardData }) {
  const s = data.summary;

  return (
    <div className="space-y-5">
      {/* 핵심 지표 */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          { label: "총지출", value: won(s.총지출) },
          { label: "월평균", value: won(s.월평균) },
          { label: "거래건수", value: `${s.거래건수}건` },
          { label: "건당평균", value: won(s.건당평균) },
        ].map((m) => (
          <div
            key={m.label}
            className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
          >
            <div className="text-xs font-semibold text-slate-400">{m.label}</div>
            <div className="mt-1 text-lg font-extrabold text-white md:text-xl">
              {m.value}
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* 카테고리 도넛 */}
        <Card title="카테고리별 지출">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={data.categories}
                dataKey="합계"
                nameKey="category"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={2}
                label={(e) => `${e.category} ${e.비중}%`}
                labelLine={false}
                fontSize={11}
              >
                {data.categories.map((_, i) => (
                  <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(v: number) => won(v)}
              />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        {/* 월별 추이 */}
        <Card title="월별 지출 추이">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.monthly}>
              <XAxis dataKey="year_month" stroke="#64748B" fontSize={11} />
              <YAxis tickFormatter={short} stroke="#64748B" fontSize={11} width={36} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => won(v)} />
              <Bar dataKey="합계" radius={[8, 8, 0, 0]} fill="#60A5FA" />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* 요일별 */}
        <Card title="요일별 지출">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data.weekday}>
              <XAxis dataKey="요일" stroke="#64748B" fontSize={11} />
              <YAxis tickFormatter={short} stroke="#64748B" fontSize={11} width={36} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => won(v)} />
              <Bar dataKey="합계" radius={[8, 8, 0, 0]} fill="#A78BFA" />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* 시간대별 */}
        <Card title="시간대별 지출">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data.timeBucket}>
              <XAxis dataKey="시간대" stroke="#64748B" fontSize={11} />
              <YAxis tickFormatter={short} stroke="#64748B" fontSize={11} width={36} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => won(v)} />
              <Bar dataKey="합계" radius={[8, 8, 0, 0]} fill="#34D399" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* 상위 가맹점 */}
      <Card title="지출 상위 가맹점">
        <div className="divide-y divide-white/5">
          {data.topMerchants.map((m, i) => (
            <div key={i} className="flex items-center justify-between py-2.5">
              <div className="flex items-center gap-3">
                <span className="w-5 text-sm font-bold text-slate-500">{i + 1}</span>
                <div>
                  <div className="text-sm font-semibold text-white">{m.가맹점}</div>
                  <div className="text-xs text-slate-400">
                    {m.카테고리} · {m.건수}건
                  </div>
                </div>
              </div>
              <div className="text-sm font-bold text-slate-200">{won(m.합계)}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
