import requests
import json

def test_workflow():
    print("⏳ جاري الاتصال بخلفية النظام (Backend) عبر Supabase...")
    
    url = "http://localhost:8000/api/v1/m2/analyze"
    payload = {
        "trigger_source": "cron",
        "language": "ar"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Format message exactly like n8n Code Node
        message = "*تقرير تحليل المخزون اليومي (نظام وكيل)* 📊\n\n"
        summary = data.get("scan_summary", {})
        message += f"📦 إجمالي المنتجات التي تم فحصها: {summary.get('total_products_checked', 0)}\n"
        message += f"📉 منتجات منخفضة المخزون: {summary.get('low_stock_count', 0)}\n"
        message += f"⚠️ تنبؤ بنقص المخزون (استباقي): {summary.get('predicted_shortage_count', 0)}\n"
        message += f"🐢 منتجات بطيئة الحركة: {summary.get('slow_moving_count', 0)}\n"
        message += f"⏳ منتجات تقترب من انتهاء الصلاحية: {summary.get('near_expiry_count', 0)}\n\n"
        
        alerts = data.get("alerts", [])
        if alerts:
            message += "*🚨 التنبيهات التفصيلية:*\n"
            for index, alert in enumerate(alerts):
                type_ar = alert.get("alert_type")
                if type_ar == 'predicted_shortage': type_ar = 'نقص متوقع'
                elif type_ar == 'low_stock': type_ar = 'مخزون منخفض'
                elif type_ar == 'slow_moving': type_ar = 'بطيء الحركة'
                elif type_ar == 'near_expiry': type_ar = 'قريب الانتهاء'
                
                details = ""
                metadata = alert.get("metadata", {})
                if alert.get("alert_type") == 'predicted_shortage' and metadata and metadata.get("days_until_stockout"):
                    details = f" (ينتهي خلال {round(metadata.get('days_until_stockout'))} يوم)"
                
                message += f"{index + 1}. [{type_ar}] منتج رقم: {alert.get('product_id')}{details}\n"
        
        rfq_drafts = data.get("rfq_drafts", [])
        if rfq_drafts:
            message += f"\n*📝 مسودات طلبات عروض الأسعار (RFQ):* تم إنشاء {len(rfq_drafts)} مسودة.\n"
            
        pricing_recs = data.get("pricing_recs", [])
        if pricing_recs:
            message += f"\n*💰 توصيات التسعير:* تم اقتراح {len(pricing_recs)} تعديل للأسعار.\n"
            
        print("\n✅ تم جلب البيانات بنجاح! إليكِ شكل رسالة الواتساب/الإيميل التي سيرسلها n8n:\n")
        print("="*50)
        print(message)
        print("="*50)

    except Exception as e:
        print(f"❌ حدث خطأ أثناء الاتصال بالـ Backend: {e}")

if __name__ == "__main__":
    test_workflow()
