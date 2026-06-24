import React from 'react';
import { AlertData, InventoryProduct } from '@/types/m2';

interface AlertsPanelProps {
  alerts: AlertData[];
  products: InventoryProduct[];
}

export const AlertsPanel: React.FC<AlertsPanelProps> = ({ alerts, products }) => {
  return (
    <div className="bg-gray-900 rounded-lg shadow-sm border border-gray-800 overflow-hidden mt-6">
      <div className="px-4 py-5 sm:px-6 bg-gray-800 border-b border-orange-800/50 flex justify-between items-center">
        <div>
          <h3 className="text-lg leading-6 font-medium text-orange-400">تنبيهات الذكاء الاصطناعي</h3>
          <p className="mt-1 max-w-2xl text-sm text-orange-300">توصيات المساعد الذكي بناءً على تحليل المخزون.</p>
        </div>
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-orange-900/50 text-orange-200">
          {alerts.length} تنبيهات
        </span>
      </div>
      <div className="p-4">
        {alerts.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-4">لا توجد تنبيهات حالية.</p>
        ) : (
          <div className="space-y-4">
            {alerts.map((alert) => {
              const product = products.find(p => p.product_id === alert.product_id);
              return (
                <div key={alert.alert_id} className="border border-orange-800/30 rounded-md p-4 bg-gray-800">
                  <div className="flex justify-between mb-2">
                    <h4 className="text-md font-bold text-white">{product?.name_ar || 'منتج غير معروف'}</h4>
                    <span className="text-xs font-semibold text-orange-500 uppercase tracking-wider">{alert.alert_type.replace('_', ' ')}</span>
                  </div>
                  <p className="text-gray-300 text-sm mb-3">
                    {alert.metadata?.message || 'لم يتم توليد تفاصيل التنبيه.'}
                  </p>
                  <div className="text-xs text-gray-400 flex gap-4">
                    <span>الرصيد: <strong className="text-gray-300">{alert.metadata?.current_quantity}</strong></span>
                    <span>الحد الأدنى: <strong className="text-gray-300">{alert.metadata?.reorder_point}</strong></span>
                    {alert.metadata?.days_until_stockout && (
                      <span>أيام للنفاذ: <strong className="text-gray-300">{alert.metadata.days_until_stockout.toFixed(1)}</strong></span>
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
