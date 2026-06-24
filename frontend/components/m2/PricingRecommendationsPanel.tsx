import React from 'react';
import { PricingRecData, InventoryProduct } from '@/types/m2';

interface PricingRecommendationsPanelProps {
  recommendations: PricingRecData[];
  products: InventoryProduct[];
}

export const PricingRecommendationsPanel: React.FC<PricingRecommendationsPanelProps> = ({ recommendations, products }) => {
  return (
    <div className="bg-gray-900 rounded-lg shadow-sm border border-gray-800 overflow-hidden">
      <div className="px-4 py-5 sm:px-6 bg-gray-800 border-b border-orange-800 flex justify-between items-center">
        <div>
          <h3 className="text-lg leading-6 font-medium text-orange-400">مساعد التسعير (Pricing Advisor)</h3>
          <p className="mt-1 max-w-2xl text-sm text-orange-300">توصيات خصم وتسعير للمنتجات بطيئة الحركة أو قريبة الانتهاء.</p>
        </div>
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-orange-900 text-orange-200">
          {recommendations.length} توصيات
        </span>
      </div>
      <div className="p-4 bg-gray-900">
        {recommendations.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-4">لا توجد توصيات تسعير حالية.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recommendations.map((rec, index) => {
              const product = products.find(p => p.product_id === rec.product_id);
              return (
                <div key={index} className="border border-orange-800 rounded-md p-4 bg-gray-800 shadow-sm flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <h4 className="text-md font-bold text-white">{product?.name_ar || 'منتج غير معروف'}</h4>
                      <span className="text-xs font-semibold text-orange-400 bg-orange-900/50 px-2 py-1 rounded">SKU: {product?.sku}</span>
                    </div>
                    <div className="bg-orange-900/20 p-3 rounded-md border border-orange-800/50 text-gray-200 text-sm mb-4 leading-relaxed font-medium">
                      {rec.recommendation}
                    </div>
                  </div>
                  <div className="text-xs text-gray-400 flex flex-wrap gap-4 pt-3 border-t border-gray-700">
                    <span>الرصيد: <strong className="text-gray-300">{product?.quantity}</strong></span>
                    {product?.expiry_date && (
                      <span>تاريخ الانتهاء: <strong className="text-red-400">{new Date(product.expiry_date).toLocaleDateString()}</strong></span>
                    )}
                    {product?.status === 'slow_moving' && (
                      <span className="text-orange-500 font-semibold">بطيء الحركة</span>
                    )}
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
