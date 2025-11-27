'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { dashboardAPI } from '@/lib/api';
import { formatDuration, formatTimestamp, getLanguageFlag, getLanguageName } from '@/lib/utils';
import { Phone, Eye } from 'lucide-react';

interface CallLogProps {
  businessId: string;
}

export default function CallLog({ businessId }: CallLogProps) {
  const [calls, setCalls] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (businessId) {
      loadCalls();
    }
  }, [businessId]);

  const loadCalls = async () => {
    try {
      const response = await dashboardAPI.getRecentCalls(businessId);
      setCalls(response.data || []);
    } catch (error) {
      console.error('Error loading calls:', error);
      setCalls([]);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: any = {
      'completed': 'default',
      'in-progress': 'secondary',
      'failed': 'destructive',
    };
    return <Badge variant={variants[status] || 'outline'}>{status}</Badge>;
  };

  if (loading) {
    return <div>Loading calls...</div>;
  }

  if (calls.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5" />
            Recent Calls
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12 text-gray-500">
            <Phone className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No calls yet. Make a test call to get started!</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Phone className="h-5 w-5" />
          Recent Calls ({calls.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Caller</TableHead>
              <TableHead>Language</TableHead>
              <TableHead>Intent</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Time</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {calls.map((call) => (
              <TableRow key={call.id}>
                <TableCell className="font-medium">{call.caller_number}</TableCell>
                <TableCell>
                  <span className="flex items-center gap-1">
                    {getLanguageFlag(call.detected_language)}
                    <span className="text-xs">{getLanguageName(call.detected_language)}</span>
                  </span>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">{call.intent || 'N/A'}</Badge>
                </TableCell>
                <TableCell>{formatDuration(call.duration_seconds)}</TableCell>
                <TableCell>{getStatusBadge(call.status)}</TableCell>
                <TableCell className="text-sm text-gray-500">
                  {formatTimestamp(call.started_at)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
