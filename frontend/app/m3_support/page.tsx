"use client";

import React, { useState } from "react";

export default function CustomerSupportPage() {
  const [query, setQuery] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [identifierType, setIdentifierType] = useState("order_id");
  const [response, setResponse] = useState<any>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // In future integration sprints, this will fetch from /api/v1/support/query
    setResponse({
      status: "mock",
      message: "Frontend routes are structured. Integration will occur in Sprint 5.",
      data: {
        query,
        identifier: { type: identifierType, value: identifier }
      }
    });
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <header className="border-b pb-4">
        <h1 className="text-3xl font-bold tracking-tight">Customer Support Agent (M3)</h1>
        <p className="text-muted-foreground mt-1">
          Structured placeholder page for customer query parser and agent dashboard.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="space-y-4 bg-card p-6 border rounded-lg shadow-sm">
        <h2 className="text-xl font-semibold">Submit Support Request</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Identifier Type</label>
            <select
              value={identifierType}
              onChange={(e) => setIdentifierType(e.target.value)}
              className="p-2 border rounded"
            >
              <option value="order_id">Order ID</option>
              <option value="invoice_id">Invoice ID</option>
              <option value="customer_id">Customer ID</option>
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Identifier Value</label>
            <input
              type="text"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="e.g. ORD-2024-1567"
              className="p-2 border rounded"
              required
            />
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium">Problem Description</label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe the customer issue here..."
            className="p-2 border rounded min-h-[100px]"
            required
          />
        </div>
        <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Parse Query & Fetch Data
        </button>
      </form>

      {response && (
        <div className="p-4 bg-muted border rounded-lg">
          <h3 className="font-semibold text-lg">Agent Raw Output State:</h3>
          <pre className="mt-2 text-xs overflow-x-auto bg-black text-green-400 p-4 rounded">
            {JSON.stringify(response, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
