export type IdentifierType = "order_id" | "invoice_id" | "customer_id";

export type IssueType =
  | "status_inquiry"
  | "billing_dispute"
  | "shipping_issue"
  | "refund_request"
  | "general_complaint";

export type ConfidenceLevel = "High" | "Medium" | "Low";

export interface InvoiceData {
  number: string;
  date: string;
  amount: number;
  status: string;
  line_items?: Array<{ description: string; amount: number }>;
}

export interface OrderData {
  id: string;
  status: string;
  items?: string[];
  total_amount?: number;
  estimated_delivery?: string;
  created_at?: string;
}

export interface ShippingData {
  tracking_id: string;
  carrier: string;
  location: string;
  status: string;
  last_update: string;
}

export interface HistoryEntry {
  date: string;
  issue_type: string;
  resolution: string;
  interaction_type?: string;
}

export interface TransparencyData {
  invoice: InvoiceData | null;
  order: OrderData | null;
  shipping: ShippingData | null;
  history: HistoryEntry[] | null;
}

export interface RejectionContext {
  reason: string;
  feedback: string;
  previous_draft: string;
}

export interface M3Response {
  draft_response: string;
  confidence_score: number;
  confidence_label: ConfidenceLevel;
  review_required: boolean;
  escalation_needed: boolean;
  issue_type: IssueType;
  transparency_data: TransparencyData;
  missing_fields: string[];
}
