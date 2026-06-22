import React, { useState } from 'react';
import { RFQDraftData, InventoryProduct } from '@/types/m2';

interface RFQDraftViewProps {
  drafts: RFQDraftData[];
  products: InventoryProduct[];
}

export const RFQDraftView: React.FC<RFQDraftViewProps> = ({ drafts, products }) => {
  const [approvedIds, setApprovedIds] = useState<Set<string>>(new Set());

  const handleApprove = (rfqId: string) => {
    // In Phase 2, this will call the backend to approve and send.
    // For Sprint 3, we just mark it locally as approved.
    setApprovedIds(prev => {
      const next = new Set(prev);
      next.add(rfqId);
      return next;
    });
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden mt-6">
      <div className="px-4 py-5 sm:px-6 bg-blue-50 border-b border-blue-100 flex justify-between items-center">
        <div>
          <h3 className="text-lg leading-6 font-medium text-blue-900">مسودات طلبات عروض الأسعار (RFQ)</h3>
          <p className="mt-1 max-w-2xl text-sm text-blue-700">تم إنشاؤها تلقائياً بواسطة الذكاء الاصطناعي وجاهزة للاعتماد.</p>
        </div>
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
          {drafts.length} مسودة
        </span>
      </div>
      <div className="p-4">
        {drafts.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">لا توجد مسودات حالية.</p>
        ) : (
          <div className="space-y-6">
            {drafts.map((draft) => {
              const product = products.find(p => p.product_id === draft.product_id);
              const isApproved = approvedIds.has(draft.rfq_id);
              
              return (
                <div key={draft.rfq_id} className={`border rounded-md overflow-hidden ${isApproved ? 'border-green-300' : 'border-gray-200'}`}>
                  <div className={`px-4 py-3 border-b flex justify-between items-center ${isApproved ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'}`}>
                    <h4 className="text-md font-bold text-gray-900">
                      طلب شراء لـ: {product?.name_ar || 'منتج غير معروف'}
                    </h4>
                    {isApproved ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        معتمد (Approved)
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        مسودة (Draft)
                      </span>
                    )}
                  </div>
                  <div className="p-4 bg-white">
                    <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans border-l-4 border-gray-300 pl-4 py-2">
                      {draft.draft_text}
                    </pre>
                  </div>
                  <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex justify-end">
                    <button
                      onClick={() => handleApprove(draft.rfq_id)}
                      disabled={isApproved}
                      className={`px-4 py-2 text-sm font-medium rounded-md shadow-sm text-white ${
                        isApproved 
                          ? 'bg-gray-400 cursor-not-allowed' 
                          : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
                      }`}
                    >
                      {isApproved ? 'تم الاعتماد' : 'اعتماد وإرسال (Approve & Send)'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
