import { supabaseAdmin } from '@/lib/supabase';
import { MARKET_CONFIG } from '@/config/market';
import { differenceInDays, parseISO } from 'date-fns';

export async function runAgingAgent(): Promise<{
  processed: number;
  snapshot: Record<string, number>;
}> {
  const sb = supabaseAdmin();
  const today = new Date();

  // Fetch all pending invoices
  const { data: invoices } = await sb
    .from('invoices')
    .select('id, due_date, amount_ttc, client_id')
    .in('status', ['pending', 'overdue', 'partial']);

  if (!invoices || invoices.length === 0) {
    return { processed: 0, snapshot: {} };
  }

  const snapshot = {
    bucket_0_30: 0,
    bucket_31_60: 0,
    bucket_61_90: 0,
    bucket_90_plus: 0,
  };

  let processed = 0;

  for (const invoice of invoices) {
    const daysOverdue = Math.max(
      0,
      differenceInDays(today, parseISO(invoice.due_date))
    );

    // Determine bucket
    let bucket = '0-30j';
    let agingRisk = 'low';

    for (const b of MARKET_CONFIG.buckets) {
      if (daysOverdue >= b.min && daysOverdue <= b.max) {
        bucket = b.label;
        agingRisk = b.risk;
        break;
      }
    }

    // Update invoice
    await sb.from('invoices').update({
      days_overdue: daysOverdue,
      bucket,
      aging_risk: agingRisk,
      status: daysOverdue > 0 ? 'overdue' : 'pending',
      updated_at: new Date().toISOString(),
    }).eq('id', invoice.id);

    // Accumulate snapshot
    if (daysOverdue <= 30)       snapshot.bucket_0_30   += invoice.amount_ttc;
    else if (daysOverdue <= 60)  snapshot.bucket_31_60  += invoice.amount_ttc;
    else if (daysOverdue <= 90)  snapshot.bucket_61_90  += invoice.amount_ttc;
    else                          snapshot.bucket_90_plus += invoice.amount_ttc;

    processed++;
  }

  // Save weekly snapshot
  await sb.from('aging_snapshots').insert({
    snapshot_date: today.toISOString().split('T')[0],
    total_outstanding: Object.values(snapshot).reduce((a, b) => a + b, 0),
    ...snapshot,
    nb_invoices_overdue: invoices.filter(i =>
      differenceInDays(today, parseISO(i.due_date)) > 0
    ).length,
  });

  // Update client totals
  const clientTotals: Record<string, number> = {};
  for (const inv of invoices) {
    clientTotals[inv.client_id] = (clientTotals[inv.client_id] || 0) + inv.amount_ttc;
  }
  for (const [clientId, total] of Object.entries(clientTotals)) {
    await sb.from('clients').update({
      total_outstanding: total,
      updated_at: new Date().toISOString(),
    }).eq('id', clientId);
  }

  return { processed, snapshot };
}
