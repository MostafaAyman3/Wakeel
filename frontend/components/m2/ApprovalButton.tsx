'use client';

import React, { useState } from 'react';

interface ApprovalButtonProps {
  rfqId: string;
  currentStatus: string;
  onApproved?: (rfqId: string) => void;
  onRejected?: (rfqId: string) => void;
}

export const ApprovalButton: React.FC<ApprovalButtonProps> = ({
  rfqId,
  currentStatus,
  onApproved,
  onRejected,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<'approved' | 'rejected' | null>(null);

  const isDraft = currentStatus === 'draft' || currentStatus === 'pending';

  const handleDecision = async (decision: 'approved' | 'rejected') => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const res = await fetch(`${baseUrl}/api/v1/m2/rfqs/${rfqId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approval_status: decision }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      setDone(decision);
      if (decision === 'approved') onApproved?.(rfqId);
      else onRejected?.(rfqId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  if (done === 'approved') {
    return (
      <span className="inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium bg-green-900 text-green-200">
        تم الاعتماد والإرسال
      </span>
    );
  }

  if (done === 'rejected') {
    return (
      <span className="inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium bg-red-900 text-red-200">
        تم الرفض
      </span>
    );
  }

  if (!isDraft) {
    const statusLabels: Record<string, string> = {
      sent: 'تم الإرسال',
      cancelled: 'ملغي',
      rejected: 'مرفوض',
    };
    return (
      <span className="inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium bg-gray-700 text-gray-300">
        {statusLabels[currentStatus] || currentStatus}
      </span>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex gap-2">
        <button
          onClick={() => handleDecision('approved')}
          disabled={loading}
          className={`px-4 py-2 text-sm font-medium rounded-md shadow-sm text-white transition-colors ${
            loading
              ? 'bg-orange-400 cursor-not-allowed'
              : 'bg-orange-600 hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-500'
          }`}
        >
          {loading ? 'جاري الإرسال...' : 'اعتماد وإرسال'}
        </button>
        <button
          onClick={() => handleDecision('rejected')}
          disabled={loading}
          className={`px-4 py-2 text-sm font-medium rounded-md shadow-sm text-white transition-colors ${
            loading
              ? 'bg-gray-600 cursor-not-allowed'
              : 'bg-red-700 hover:bg-red-800 focus:outline-none focus:ring-2 focus:ring-red-500'
          }`}
        >
          رفض
        </button>
      </div>
      {error && (
        <p className="text-xs text-red-400 mt-1">{error}</p>
      )}
    </div>
  );
};
