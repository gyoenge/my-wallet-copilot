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
}

export interface WeekdayRow {
  요일: string;
  합계: number;
  건수: number;
  건당평균: number;
}

export interface TimeBucketRow {
  시간대: string;
  합계: number;
  건수: number;
}

export interface MerchantRow {
  가맹점: string;
  카테고리: string;
  합계: number;
  건수: number;
}

export interface Dashboard {
  summary: Summary;
  health: { score: number; label: string };
  insights: string[];
  categories: CategoryRow[];
  monthly: MonthlyRow[];
  weekday: WeekdayRow[];
  timeBucket: TimeBucketRow[];
  topMerchants: MerchantRow[];
  recentChange: { category: string; 이전달: number; 최근달: number; 증감액: number }[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}
