'use client';

import React, { useState, useEffect } from 'react';
import { InventoryTable } from '@/components/m2/InventoryTable';
import { AlertsPanel } from '@/components/m2/AlertsPanel';
import { RFQDraftView } from '@/components/m2/RFQDraftView';
import { PricingRecommendationsPanel } from '@/components/m2/PricingRecommendationsPanel';
import { InventoryStatusResponse, AnalyzeResponse } from '@/types/m2';

export default function M2Dashboard() {
  const [inventoryData, setInventoryData] = useState<InventoryStatusResponse | null>(null);
  const [analyzeData, setAnalyzeData] = useState<AnalyzeResponse | null>(null);
  const [loadingInventory, setLoadingInventory] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchInventory = async () => {
    setLoadingInventory(true);
    setError(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/m2/inventory`);
      if (!response.ok) throw new Error('Failed to fetch inventory');
      const data: InventoryStatusResponse = await response.json();
      setInventoryData(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(String(err));
      }
    } finally {
      setLoadingInventory(false);
    }
  };

  useEffect(() => {
    fetchInventory();
  }, []);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/m2/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trigger_source: 'manual', language: 'ar-EG' }),
      });
      if (!response.ok) throw new Error('Failed to run analysis');
      const data: AnalyzeResponse = await response.json();
      setAnalyzeData(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(String(err));
      }
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-black py-8 px-4 sm:px-6 lg:px-8" dir="rtl">
      <div className="max-w-7xl mx-auto space-y-8">

        {/* Header */}
        <div className="md:flex md:items-center md:justify-between bg-gray-900 p-6 rounded-lg shadow-sm border border-gray-800">
          <div className="flex-1 min-w-0">
            <h2 className="text-2xl font-bold leading-7 text-white sm:text-3xl sm:truncate">
              لوحة تحكم المشتريات والمخزون (M2)
            </h2>
            <p className="mt-1 text-sm text-gray-400">
              إدارة المخزون الذكية المدعومة بالذكاء الاصطناعي (Agentic AI)
            </p>
          </div>
          <div className="mt-4 flex md:mt-0 md:mr-4 space-x-3 space-x-reverse">
            <button
              type="button"
              onClick={fetchInventory}
              disabled={loadingInventory}
              className="inline-flex items-center px-4 py-2 border border-gray-700 rounded-md shadow-sm text-sm font-medium text-gray-200 bg-gray-800 hover:bg-gray-700 focus:outline-none"
            >
              تحديث الأرصدة
            </button>
            <button
              type="button"
              onClick={handleAnalyze}
              disabled={analyzing}
              className={`inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white focus:outline-none ${analyzing ? 'bg-orange-400 cursor-not-allowed' : 'bg-orange-600 hover:bg-orange-700'
                }`}
            >
              {analyzing ? 'جاري التحليل...' : 'تشغيل الذكاء الاصطناعي (Analyze)'}
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border-l-4 border-red-400 p-4">
            <div className="flex">
              <div className="ml-3">
                <p className="text-sm text-red-700">حدث خطأ: {error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Dashboard Content */}
        {loadingInventory && !inventoryData ? (
          <div className="text-center py-12">
            <p className="text-gray-400">جاري تحميل بيانات المخزون...</p>
          </div>
        ) : (
          <>
            {/* Inventory Table */}
            {inventoryData && <InventoryTable products={inventoryData.products} />}

            {/* AI Results */}
            {analyzeData && inventoryData && (
              <div className="flex flex-col gap-6 mt-8">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <AlertsPanel alerts={analyzeData.alerts} products={inventoryData.products} />
                  <RFQDraftView drafts={analyzeData.rfq_drafts} products={inventoryData.products} />
                </div>
                {analyzeData.pricing_recs && analyzeData.pricing_recs.length > 0 && (
                  <PricingRecommendationsPanel
                    recommendations={analyzeData.pricing_recs}
                    products={inventoryData.products}
                  />
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
