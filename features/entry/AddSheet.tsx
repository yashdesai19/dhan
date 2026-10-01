import { Fragment } from 'react';
import { useRouter } from 'expo-router';

import { IconTile, ListRow, Sheet, useSheet, type IconName, type Tone } from '@/components';
import { Divider } from '@/components/ui/Lists';

const OPTIONS: { title: string; body: string; icon: IconName; tone: Tone; href: string }[] = [
  {
    title: 'Add expense',
    body: 'Amount, category, done. About 3 seconds.',
    icon: 'up',
    tone: 'expense',
    href: '/add/expense',
  },
  {
    title: 'Add income',
    body: 'Salary, freelance, gifts, cashback.',
    icon: 'down',
    tone: 'income',
    href: '/add/income',
  },
  {
    title: 'Transfer',
    body: 'Move money between your accounts.',
    icon: 'transfer',
    tone: 'neutral',
    href: '/add/transfer',
  },
  {
    title: 'Split expense',
    body: 'Share a bill with friends or a group.',
    icon: 'users',
    tone: 'neutral',
    href: '/add/split',
  },
];

function Options() {
  const router = useRouter();
  const { close } = useSheet();
  return (
    <>
      {OPTIONS.map((o, i) => (
        <Fragment key={o.href}>
          {i > 0 ? <Divider /> : null}
          <ListRow
            leading={<IconTile icon={o.icon} tone={o.tone} size="lg" />}
            title={o.title}
            subtitle={o.body}
            chevron
            pad={14}
            onPress={() => close(() => router.push(o.href))}
          />
        </Fragment>
      ))}
    </>
  );
}

/** Centre Add button → Add expense, Add income, Transfer, Split expense (AddSheet artboard). */
export function AddSheetScreen() {
  return (
    <Sheet title="Add" label="Add">
      <Options />
    </Sheet>
  );
}
