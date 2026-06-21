export interface Summary {
  총지출: number;
  거래건수: number;
  건당평균: number;
  월평균: number;
  분석개월수: number;
  시작일: string;
  종료일: string;
}

export interface CategoryRow {
  category: string;
  합계: number;
  건수: number;
  비중: number;
}

export interface MonthlyRow {
  year_month: string;
  합계: number;
  건수: number;
  "전월대비금액": number | null;
  "전월대비%": number | null;
  partial: boolean;
}

// 데이터에 따라 동적으로 추가되는 분석 카드.
export type DashCard =
  | {
      kind: "bars";
      title: string;
      gradient: [string, string];
      bars: { label: string; value: number }[];
    }
  | {
      kind: "list";
      title: string;
      items: { name: string; sub: string; value: string }[];
    }
  | { kind: "savings"; title: string; text: string }
  | {
      kind: "clusters";
      title: string;
      subtitle: string;
      clusters: {
        label: string;
        size: number;
        share: number;
        freq: number;
        avg: number;
        weekend: number;
        night: number;
        categories: string[];
        examples: string[];
      }[];
    }
  | {
      kind: "goal";
      title: string;
      category: string;
      note: string;
      target: number;
      baseline: number;
      actual: number;
      lastMonth: string;
      progress: number;
      achieved: boolean;
      gap: number;
      forecast: number;
      onTrack: boolean;
    };

export interface Dashboard {
  summary: Summary;
  health: { score: number; label: string };
  insights: string[];
  categories: CategoryRow[];
  monthly: MonthlyRow[];
  cards: DashCard[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}
