export interface InventoryProduct {
  product_id: string;
  sku: string;
  name: string;
  name_ar: string;
  category: string;
  quantity: number;
  reorder_point: number;
  lead_time_days: number;
  avg_daily_sales: number;
  days_until_stockout: number;
  status: 'safe' | 'low_stock' | 'predicted_shortage' | 'slow_moving' | 'near_expiry';
  expiry_date: string | null;
}

export interface InventorySummary {
  total: number;
  low_stock: number;
  predicted_shortage: number;
  slow_moving: number;
  near_expiry: number;
  safe: number;
}

export interface InventoryStatusResponse {
  products: InventoryProduct[];
  summary: InventorySummary;
}

export interface AlertData {
  alert_id: string;
  product_id: string;
  alert_type: string;
  metadata: Record<string, any>;
}

export interface RFQDraftData {
  rfq_id: string;
  product_id: string;
  draft_text: string;
}

export interface PricingRecData {
  product_id: string;
  recommendation: string;
}

export interface AnalyzeResponse {
  scan_summary: Record<string, any>;
  alerts: AlertData[];
  rfq_drafts: RFQDraftData[];
  pricing_recs: PricingRecData[];
  language: string;
}
