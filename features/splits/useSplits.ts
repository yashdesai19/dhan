import { useMemo } from 'react';

import { useGroupExpenses, useGroups, usePeople, useSettlements } from '@/data/queries';
import type { AvatarTone, ID, Person } from '@/types/domain';
import { groupPosition, overallPosition } from '@/utils/splits';

export const ME = 'me';

/** People, groups, expenses and settlements with the derived positions (spec §6 invariants). */
export function useSplits() {
  const people = usePeople();
  const groups = useGroups();
  const expenses = useGroupExpenses();
  const settlements = useSettlements();
  const loading = people.isPending || groups.isPending || expenses.isPending || settlements.isPending;

  return useMemo(() => {
    const ps = people.data ?? [];
    const person = (id: ID): Person =>
      ps.find((p) => p.id === id) ?? {
        id,
        name: id,
        initials: id.slice(0, 2).toUpperCase(),
        avatarTone: 'green' as AvatarTone,
      };
    const ex = expenses.data ?? [];
    return {
      loading,
      people: ps,
      person,
      groups: groups.data ?? [],
      expenses: ex,
      settlements: settlements.data ?? [],
      overall: overallPosition(ex, settlements.data ?? [], ME),
      groupPos: (groupId: ID) => groupPosition(ex, groupId, ME),
    };
  }, [people.data, groups.data, expenses.data, settlements.data, loading]);
}
