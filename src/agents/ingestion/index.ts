import * as XLSX from 'xlsx';
import { supabaseAdmin } from '@/lib/supabase';

export interface RawInvoiceRow {
  client_id: string;
  client_name: string;
  invoice_number: string;
  amount_ht: number;
  amount_ttc: number;
  issue_date: string;
  due_date: string;
  status: string;
  description?: string;
}

export async function parseExcelFile(buffer: Buffer): Promise<RawInvoiceRow[]> {
  const workbook = XLSX.read(buffer, { type: 'buffer', cellDates: true });
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json(sheet, { raw: false });

  return rows.map((row: any) => ({
    client_id: String(row['ID Client'] || row['client_id'] || ''),
    client_name: String(row['Nom Client'] || row['client_name'] || ''),
    invoice_number: String(row['N° Facture'] || row['invoice_number'] || ''),
    amount_ht: parseFloat(String(row['Montant HT'] || row['amount_ht'] || '0').replace(',', '.')),
    amount_ttc: parseFloat(String(row['Montant TTC'] || row['amount_ttc'] || '0').replace(',', '.')),
    issue_date: String(row['Date Facture'] || row['issue_date'] || ''),
    due_date: String(row['Date Échéance'] || row['due_date'] || ''),
    status: String(row['Statut'] || row['status'] || 'pending'),
    description: String(row['Description'] || row['description'] || ''),
  }));
}

export async function upsertInvoices(rows: RawInvoiceRow[]): Promise<{
  inserted: number;
  updated: number;
  errors: string[];
}> {
  const sb = supabaseAdmin();
  let inserted = 0;
  let updated = 0;
  const errors: string[] = [];

  for (const row of rows) {
    try {
      // Upsert client
      const { data: client } = await sb
        .from('clients')
        .upsert({
          external_id: row.client_id,
          name: row.client_name,
        }, { onConflict: 'external_id' })
        .select('id')
        .single();

      if (!client) {
        errors.push(`Client not found/created: ${row.client_id}`);
        continue;
      }

      // Upsert invoice
      const { data: existing } = await sb
        .from('invoices')
        .select('id')
        .eq('external_id', row.invoice_number)
        .single();

      if (existing) {
        await sb.from('invoices').update({
          status: row.status,
          updated_at: new Date().toISOString(),
        }).eq('id', existing.id);
        updated++;
      } else {
        await sb.from('invoices').insert({
          external_id: row.invoice_number,
          client_id: client.id,
          invoice_number: row.invoice_number,
          amount_ht: row.amount_ht,
          amount_ttc: row.amount_ttc,
          currency: 'MAD',
          issue_date: row.issue_date,
          due_date: row.due_date,
          status: row.status,
          description: row.description,
        });
        inserted++;
      }
    } catch (e: any) {
      errors.push(`Error on invoice ${row.invoice_number}: ${e.message}`);
    }
  }

  return { inserted, updated, errors };
}
