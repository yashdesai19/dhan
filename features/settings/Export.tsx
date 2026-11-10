import { useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { File, Paths } from 'expo-file-system';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';

import { Banner, Button, IconButton, KpiTile, Screen, Text, TopBar } from '@/components';
import { BookSwitcher } from '@/features/shared/BookSwitcher';
import { useActiveBook, useMoneyData, useToday } from '@/features/shared/hooks';
import { space } from '@/theme';
import { ALL_BOOKS_ID, profitAndLoss } from '@/utils/books';
import { monthYear, shiftMonth } from '@/utils/dates';
import { exportRows, statementHtml, toCsv } from '@/utils/export';
import { inr, plural } from '@/utils/format';

export function ExportScreen() {
  const today = useToday();
  const money = useMoneyData();
  const active = useActiveBook();
  const [month, setMonth] = useState(today.month);
  const [busy, setBusy] = useState<'pdf' | 'csv' | null>(null);
  const [error, setError] = useState<string | null>(null);

  const bookName = active.id === ALL_BOOKS_ID ? 'All books' : (active.book?.name ?? 'Personal');
  const fileBase = `DHAN ${bookName} ${month}`
    .replace(/[^\w\- ]+/g, '')
    .trim()
    .replace(/\s+/g, '-');
  const view = useMemo(
    () => ({
      rows: exportRows(money.transactions, month, money.accounts, money.categories),
      pl: profitAndLoss(money.transactions, month, money.categories),
    }),
    [money.transactions, money.accounts, money.categories, month],
  );

  const share = async (kind: 'pdf' | 'csv') => {
    setError(null);
    setBusy(kind);
    try {
      if (!(await Sharing.isAvailableAsync())) throw new Error('Sharing isn’t available on this device.');
      let uri: string;
      if (kind === 'csv') {
        const file = new File(Paths.cache, `${fileBase}.csv`);
        file.create({ overwrite: true });
        file.write(toCsv(view.rows));
        uri = file.uri;
      } else {
        const html = statementHtml({
          bookName,
          month,
          business: active.isBusiness,
          pl: view.pl,
          rows: view.rows,
        });
        uri = (await Print.printToFileAsync({ html })).uri;
      }
      await Sharing.shareAsync(uri, {
        mimeType: kind === 'csv' ? 'text/csv' : 'application/pdf',
        dialogTitle: `${bookName} · ${monthYear(month)}`,
        UTI: kind === 'csv' ? 'public.comma-separated-values-text' : 'com.adobe.pdf',
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Couldn’t create the file. Try again.');
    } finally {
      setBusy(null);
    }
  };

  return (
    <Screen gap={space[20]}>
      <TopBar title="Export data" />
      <BookSwitcher />
      <View style={styles.month}>
        <IconButton
          variant="bare"
          icon="chevL"
          accessibilityLabel="Previous month"
          onPress={() => setMonth(shiftMonth(month, -1))}
        />
        <Text variant="body" weight="semibold">
          {monthYear(month)}
        </Text>
        <IconButton
          variant="bare"
          icon="chevR"
          accessibilityLabel="Next month"
          onPress={() => month < today.month && setMonth(shiftMonth(month, 1))}
        />
      </View>
      <View style={styles.row}>
        <KpiTile label={active.isBusiness ? 'Sales' : 'Income'} value={inr(view.pl.totalIncome)} />
        <KpiTile label={active.isBusiness ? 'Expenses' : 'Spent'} value={inr(view.pl.totalExpenses)} />
      </View>
      <Text variant="small" color="muted">
        {`${bookName} · ${plural(view.rows.length, 'entry', 'entries')}. The PDF has the ${
          active.isBusiness ? 'profit and loss' : 'income and spending'
        } summary and every entry; the Excel file lists every entry.`}
      </Text>
      <Button
        label="Share PDF"
        icon="doc"
        loading={busy === 'pdf'}
        disabled={!!busy || money.loading}
        onPress={() => void share('pdf')}
      />
      <Button
        label="Share Excel (CSV)"
        kind="secondary"
        icon="download"
        loading={busy === 'csv'}
        disabled={!!busy || money.loading}
        onPress={() => void share('csv')}
      />
      {error ? (
        <Banner icon="alert" tone="error">
          {error}
        </Banner>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  month: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  row: { flexDirection: 'row', gap: space[10] },
});
