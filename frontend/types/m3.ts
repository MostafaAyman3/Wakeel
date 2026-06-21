// M3 Customer Support — TypeScript types mirroring the backend contract
// (backend/api/v1/m3_support.py).

export type IdentifierType = "order_id" | "invoice_id" | "customer_id";

export type IssueType =
  | "status_inquiry"
  | "billing_dispute"
  | "shipping_issue"
  | "refund_request"
  | "general_complaint";

export type ConfidenceLabel = "High" | "Medium" | "Low";

export interface CustomerIdentifier {
  type: IdentifierType;
  value: string;
}

export interface SupportRequest {
  query: string;
  identifier?: CustomerIdentifier | null;
  rejection_context?: Record<string, unknown> | null;
}

export interface TransparencyData {
  invoice: Record<string, unknown> | null;
  order: Record<string, unknown> | null;
  shipping: Record<string, unknown> | Array<Record<string, unknown>> | null;
  history: Array<Record<string, unknown>> | null;
}

export interface SupportResponse {
  draft_response: string;
  final_response: string;
  confidence_score: number;
  confidence_label: ConfidenceLabel;
  review_required: boolean;
  escalation_needed: boolean;
  escalation_summary: Record<string, unknown>;
  issue_type: IssueType | null;
  transparency_data: TransparencyData;
  missing_fields: string[];
}

// Review action endpoint payloads / responses
export interface ReviewActionResponse {
  case_id: string;
  action: "approved" | "rejected" | "escalated";
  final_response?: string;
  rejection_context?: Record<string, unknown>;
  escalation_reason?: string;
}

export type ReviewAction = "approve" | "reject" | "escalate";
