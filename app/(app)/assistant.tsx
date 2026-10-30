import { Redirect } from 'expo-router';

import { AssistantScreen } from '@/features/assistant/Assistant';
import { FEATURES } from '@/utils/features';

export default function AssistantRoute() {
  if (!FEATURES.DHAN_AI) {
    return <Redirect href="/" />;
  }
  return <AssistantScreen />;
}
