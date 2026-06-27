'use client';

import React from 'react';

interface Offer {
  id?: string;
  vendor_name: string;
  price_per_unit: number;
  lead_time_days?: number | null;
  payment_terms?: string | null;
  notes?: string | null;
  score?: number;
  justification?: string;
}

interface OfferComparisonViewProps {
  rfqId: string;
  offers: Offer[];
  recommendedVendor?: string | null;
}

export const OfferComparisonView: React.FC<OfferComparisonViewProps> = ({
  rfqId,
  offers,
  recommendedVendor,
}) => {
  if (!offers || offers.length === 0) {
    return (
      <div className="bg-gray-900 rounded-lg shadow-sm border border-gray-800 p-6 mt-6">
        <h3 className="text-lg font-medium text-blue-400 mb-2">مقارنة عروض الموردين</h3>
        <p className="text-sm text-gray-400 text-center py-4">
          لم يتم استلام أي عروض بعد لهذا الطلب.
        </p>
      </div>
    );
  }

  const sorted = [...offers].sort((a, b) => {
    if (a.score !== undefined && b.score !== undefined) return b.score - a.score;
    return a.price_per_unit - b.price_per_unit;
  });

  return (
    <div className="bg-gray-900 rounded-lg shadow-sm border border-gray-800 overflow-hidden mt-6">
      {/* Header */}
      <div className="px-4 py-5 sm:px-6 bg-gray-800 border-b border-blue-800 flex justify-between items-center">
        <div>
          <h3 className="text-lg leading-6 font-medium text-blue-400">
            مقارنة عروض الموردين
          </h3>
          <p className="mt-1 text-sm text-blue-300">
            تحليل العروض بواسطة الذكاء الاصطناعي — الأعلى نقاطاً يُنصح به.
          </p>
        </div>
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-900 text-blue-200">
          {offers.length} عروض
        </span>
      </div>

      {/* Recommended banner */}
      {recommendedVendor && (
        <div className="px-4 py-3 bg-green-900/30 border-b border-green-800 flex items-center gap-2">
          <span className="text-green-400 font-semibold text-sm">
            التوصية:
          </span>
          <span className="text-green-200 text-sm">{recommendedVendor}</span>
        </div>
      )}

      {/* Comparison table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-700">
          <thead className="bg-gray-800">
            <tr>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                المورد
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                السعر / الوحدة
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                مدة التوريد
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                شروط الدفع
              </th>
              {sorted.some(o => o.score !== undefined) && (
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                  النقاط
                </th>
              )}
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                ملاحظات
              </th>
            </tr>
          </thead>
          <tbody className="bg-gray-900 divide-y divide-gray-800">
            {sorted.map((offer, idx) => {
              const isRecommended = offer.vendor_name === recommendedVendor;
              return (
                <tr
                  key={offer.id || idx}
                  className={isRecommended ? 'bg-green-900/20' : undefined}
                >
                  <td className="px-4 py-3 text-sm font-medium text-white whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      {isRecommended && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-800 text-green-200">
                          موصى به
                        </span>
                      )}
                      {offer.vendor_name}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-300 whitespace-nowrap">
                    {offer.price_per_unit.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-300 whitespace-nowrap">
                    {offer.lead_time_days != null ? `${offer.lead_time_days} يوم` : '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-300">
                    {offer.payment_terms || '—'}
                  </td>
                  {sorted.some(o => o.score !== undefined) && (
                    <td className="px-4 py-3 text-sm whitespace-nowrap">
                      {offer.score !== undefined ? (
                        <span className={`font-semibold ${offer.score >= 80 ? 'text-green-400' : offer.score >= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
                          {offer.score.toFixed(0)}
                        </span>
                      ) : '—'}
                    </td>
                  )}
                  <td className="px-4 py-3 text-sm text-gray-400 max-w-xs truncate">
                    {offer.notes || '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Justification for recommended offer */}
      {sorted[0]?.justification && (
        <div className="px-4 py-4 bg-gray-800 border-t border-gray-700">
          <p className="text-xs text-gray-400 font-medium mb-1">سبب التوصية:</p>
          <p className="text-sm text-gray-300">{sorted[0].justification}</p>
        </div>
      )}
    </div>
  );
};
