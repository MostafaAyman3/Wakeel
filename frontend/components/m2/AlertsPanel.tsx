import React from 'react';
import { AlertData, InventoryProduct } from '@/types/m2';

interface AlertsPanelProps {
  alerts: AlertData[];
  products: InventoryProduct[];
}

export const AlertsPanel: React.FC<AlertsPanelProps> = ({ alerts, products }) => {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden mt-6">
      <div className="px-4 py-5 sm:px-6 bg-red-50 border-b border-red-100 flex justify-between items-center">
        <div>
          <h3 className="text-lg leading-6 font-medium text-red-900">تنبيهات الذكاء الاصطناعي</h3>
          <p className="mt-1 max-w-2xl text-sm text-red-700">توصيات المساعد الذكي بناءً على تحليل المخزون.</p>
        </div>
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
          {alerts.length} تنبيهات
        </span>
      </div>
      <div className="p-4">
        {alerts.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">لا توجد تنبيهات حالية.</p>
        ) : (
          <div className="space-y-4">
            {alerts.map((alert) => {
              const product = products.find(p => p.product_id === alert.product_id);
              return (
                <div key={alert.alert_id} className="border border-red-200 rounded-md p-4 bg-red-50/50">
                  <div className="flex justify-between mb-2">
                    <h4 className="text-md font-bold text-gray-900">{product?.name_ar || 'منتج غير معروف'}</h4>
                    <span className="text-xs font-semibold text-red-600 uppercase tracking-wider">{alert.alert_type.replace('_', ' ')}</span>
                  </div>
                  <p className="text-gray-800 text-sm mb-3">
                    {alert.metadata?.message || 'لم يتم توليد تفاصيل التنبيه.'}
                  </p>
                  <div className="text-xs text-gray-500 flex gap-4">
                    <span>الرصيد: <strong className="text-gray-700">{alert.metadata?.current_quantity}</strong></span>
                    <span>الحد الأدنى: <strong className="text-gray-700">{alert.metadata?.reorder_point}</strong></span>
                    {alert.metadata?.days_until_stockout && (
                      <span>أيام للنفاذ: <strong className="text-gray-700">{alert.metadata.days_until_stockout.toFixed(1)}</strong></span>
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
