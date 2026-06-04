import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

interface ApprovalRule {
  tool_name: string;
  level: string;
  risk: string;
  description: string;
}

const ApprovalPanel: React.FC = () => {
  const [rules, setRules] = useState<ApprovalRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [checkResult, setCheckResult] = useState<{ tool_name: string; approved: boolean } | null>(null);
  const [toolName, setToolName] = useState('');
  const [toolArgs, setToolArgs] = useState('{}');

  useEffect(() => {
    loadRules();
  }, []);

  const loadRules = async () => {
    try {
      setLoading(true);
      const data = await api.approval.rules();
      setRules(data);
      setError('');
    } catch (e: any) {
      setError(e.message || 'Failed to load approval rules');
    } finally {
      setLoading(false);
    }
  };

  const handleCheck = async () => {
    try {
      let parsedArgs = {};
      try {
        parsedArgs = JSON.parse(toolArgs);
      } catch {
        setError('Invalid JSON arguments');
        return;
      }
      const result = await api.approval.check(toolName, parsedArgs);
      setCheckResult(result);
      setError('');
    } catch (e: any) {
      setError(e.message || 'Approval check failed');
    }
  };

  const handleClearSession = async () => {
    try {
      await api.approval.clearSession();
      setError('');
    } catch (e: any) {
      setError(e.message || 'Failed to clear session');
    }
  };

  const riskColors: Record<string, string> = {
    safe: 'bg-green-100 text-green-800',
    low: 'bg-blue-100 text-blue-800',
    medium: 'bg-yellow-100 text-yellow-800',
    high: 'bg-orange-100 text-orange-800',
    critical: 'bg-red-100 text-red-800',
  };

  const levelColors: Record<string, string> = {
    always_allow: 'bg-green-100 text-green-800',
    session_allow: 'bg-blue-100 text-blue-800',
    ask_once: 'bg-yellow-100 text-yellow-800',
    always_ask: 'bg-orange-100 text-orange-800',
    always_deny: 'bg-red-100 text-red-800',
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Tool Approval</h2>
        <button
          onClick={handleClearSession}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
        >
          Clear Session
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Check Tool */}
      <div className="bg-white rounded-xl border p-4 space-y-3">
        <h3 className="font-medium text-gray-700">Check Tool Approval</h3>
        <div className="flex gap-3">
          <input
            type="text"
            value={toolName}
            onChange={(e) => setToolName(e.target.value)}
            placeholder="Tool name (e.g., execute_shell)"
            className="flex-1 px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="text"
            value={toolArgs}
            onChange={(e) => setToolArgs(e.target.value)}
            placeholder='Arguments (JSON)'
            className="flex-1 px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleCheck}
            disabled={!toolName}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Check
          </button>
        </div>
        {checkResult && (
          <div className={`p-3 rounded-lg text-sm ${checkResult.approved ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
            {checkResult.approved
              ? `Approved: ${checkResult.tool_name}`
              : `Denied: ${checkResult.tool_name}`}
          </div>
        )}
      </div>

      {/* Rules List */}
      <div className="bg-white rounded-xl border">
        <div className="p-4 border-b">
          <h3 className="font-medium text-gray-700">Approval Rules</h3>
        </div>
        {loading ? (
          <div className="p-4 text-center text-gray-500">Loading...</div>
        ) : rules.length === 0 ? (
          <div className="p-4 text-center text-gray-400">No custom rules defined</div>
        ) : (
          <div className="divide-y">
            {rules.map((rule, i) => (
              <div key={i} className="p-4 flex items-center justify-between">
                <div>
                  <span className="font-mono text-sm font-medium">{rule.tool_name}</span>
                  {rule.description && (
                    <p className="text-xs text-gray-500 mt-0.5">{rule.description}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${riskColors[rule.risk] || 'bg-gray-100 text-gray-700'}`}>
                    {rule.risk}
                  </span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${levelColors[rule.level] || 'bg-gray-100 text-gray-700'}`}>
                    {rule.level.replace(/_/g, ' ')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ApprovalPanel;