'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { dashboardAPI } from '@/lib/api';
import { useBusinessId } from '@/hooks/useBusinessId';
import { TrendingUp, Phone, Target } from 'lucide-react';

export default function AnalyticsPage() {
  const { businessId } = useBusinessId();
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (businessId) {
      loadAnalytics();
    }
  }, [businessId]);

  const loadAnalytics = async () => {
    if (!businessId) return;
    
    try {
      const response = await dashboardAPI.getCallAnalytics(businessId);
      setAnalytics(response.data);
    } catch (error) {
      console.error('Error loading analytics:', error);
      setAnalytics({
        total_calls: 0,
        completed_calls: 0,
        escalated_calls: 0,
        average_duration: 0,
        by_language: {},
        by_intent: {}
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-6">Loading analytics...</div>;
  }

  const languageData = Object.entries(analytics?.by_language || {})
    .filter(([, value]) => typeof value === 'number' && value > 0)
    .map(([name, value]) => ({
      name: name.toUpperCase(),
      value: value as number
    }));

  const intentData = Object.entries(analytics?.by_intent || {})
    .filter(([, value]) => typeof value === 'number' && value > 0)
    .map(([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      value: value as number
    }));

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
        <p className="text-gray-500 mt-1">Insights and performance metrics</p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Calls</CardTitle>
            <Phone className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics?.total_calls || 0}</div>
            <p className="text-xs text-muted-foreground">All time</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Duration</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {analytics?.total_calls > 0
                ? `${Math.floor((analytics?.average_duration || 0) / 60)}m ${Math.floor((analytics?.average_duration || 0) % 60)}s`
                : '0m 0s'
              }
            </div>
            <p className="text-xs text-muted-foreground">Per call</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completion Rate</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {analytics?.total_calls > 0 
                ? Math.round((analytics.completed_calls / analytics.total_calls) * 100) 
                : 0}%
            </div>
            <p className="text-xs text-muted-foreground">Success rate</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Escalation Rate</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {analytics?.total_calls > 0 
                ? Math.round((analytics.escalated_calls / analytics.total_calls) * 100) 
                : 0}%
            </div>
            <p className="text-xs text-muted-foreground">To human</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Calls by Language</CardTitle>
            <CardDescription>Distribution across supported languages</CardDescription>
          </CardHeader>
          <CardContent>
            {languageData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={languageData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {languageData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No language data yet. Make some test calls!
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Calls by Intent</CardTitle>
            <CardDescription>What customers are calling about</CardDescription>
          </CardHeader>
          <CardContent>
            {intentData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={intentData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No intent data yet. Make some test calls!
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
