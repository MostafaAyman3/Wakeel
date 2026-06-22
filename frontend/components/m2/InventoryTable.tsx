import React from 'react';
import { InventoryProduct } from '@/types/m2';

interface InventoryTableProps {
  products: InventoryProduct[];
}

export const InventoryTable: React.FC<InventoryTableProps> = ({ products }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'low_stock':
      case 'predicted_shortage':
        return 'bg-red-100 text-red-800';
      case 'near_expiry':
        return 'bg-orange-100 text-orange-800';
      case 'slow_moving':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-green-100 text-green-800';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'low_stock': return 'رصيد منخفض';
      case 'predicted_shortage': return 'عجز متوقع';
      case 'near_expiry': return 'قريب الانتهاء';
      case 'slow_moving': return 'بطيء الحركة';
      default: return 'آمن';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="px-4 py-5 sm:px-6 bg-gray-50 border-b border-gray-200">
        <h3 className="text-lg leading-6 font-medium text-gray-900">حالة المخزون</h3>
        <p className="mt-1 max-w-2xl text-sm text-gray-500">نظرة عامة على جميع المنتجات النشطة وتصنيفها.</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                المنتج (SKU)
              </th>
              <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                الفئة
              </th>
              <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                الكمية / نقطة الطلب
              </th>
              <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                أيام لنفاد الكمية
              </th>
              <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                الحالة
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {products.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-4 text-center text-sm text-gray-500">
                  لا توجد منتجات
                </td>
              </tr>
            ) : (
              products.map((product) => (
                <tr key={product.product_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{product.name_ar}</div>
                    <div className="text-sm text-gray-500">{product.sku}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {product.category}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <span className={product.quantity <= product.reorder_point ? 'text-red-600 font-semibold' : ''}>
                      {product.quantity}
                    </span>
                    {' / '} {product.reorder_point}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {product.days_until_stockout.toFixed(1)} يوم
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(product.status)}`}>
                      {getStatusLabel(product.status)}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
