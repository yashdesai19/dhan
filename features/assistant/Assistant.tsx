// DHAN AI — UI only. Suggested questions return the predefined mock responses (spec §15).
import { useEffect, useRef } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import {
  ChatBubble,
  Icon,
  IconButton,
  Pill,
  SectionLabel,
  Text,
  TopBar,
  Touchable,
  TypingIndicator,
} from '@/components';
import { useTopPadding } from '@/components/navigation/Screen';
import { useAIResponses, useAskAI } from '@/data/queries';
import { useMotionDuration } from '@/hooks/feedback';
import { useAssistantStore } from '@/store/ui';
import type { AIResponse } from '@/types/domain';

/**
 * The demo's suggestions come with their answers. From the API they come without, and each is
 * answered by DHAN AI (from the user's own data) the first time it's asked.
 */
function useFetchAnswers(responses: AIResponse[], asked: AIResponse['id'][]) {
  const askAI = useAskAI().mutateAsync;
  const answers = useAssistantStore((s) => s.answers);
  const setAnswer = useAssistantStore((s) => s.setAnswer);
  const requested = useRef(new Set<string>());
  useEffect(() => {
    for (const id of asked) {
      const r = responses.find((x) => x.id === id);
      if (!r || r.answer || answers[id] || requested.current.has(id)) continue;
      requested.current.add(id);
      askAI(r.question)
        .then((a) => setAnswer(id, a))
        .catch((e: Error) => setAnswer(id, { error: e.message }))
        .finally(() => requested.current.delete(id));
    }
  }, [asked, responses, answers, askAI, setAnswer]);
  return (r: AIResponse) => (r.answer ? { answer: r.answer, stats: r.stats } : answers[r.id]);
}
import { fonts, iconSize, layout, motion, radius, size, space, textVariants, useColors } from '@/theme';

export function AssistantScreen() {
  const c = useColors();
  const insets = useSafeAreaInsets();
  const paddingTop = useTopPadding('stack');
  const responses = useAIResponses().data ?? [];
  const asked = useAssistantStore((s) => s.asked);
  const typing = useAssistantStore((s) => s.typing);
  const ask = useAssistantStore((s) => s.ask);
  const doneTyping = useAssistantStore((s) => s.doneTyping);
  const scroll = useRef<ScrollView>(null);
  const delay = useMotionDuration(motion.typing);
  const answerFor = useFetchAnswers(responses, asked);

  useEffect(() => {
    if (!typing) return;
    const t = setTimeout(doneTyping, Math.max(delay, 300));
    return () => clearTimeout(t);
  }, [typing, delay, doneTyping]);
  useEffect(() => {
    const t = setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 50);
    return () => clearTimeout(t);
  }, [asked.length, typing]);

  const suggestions = responses.filter((r) => !asked.includes(r.id));

  return (
    <KeyboardAvoidingView
      style={[styles.fill, { backgroundColor: c.bg }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        ref={scroll}
        style={styles.fill}
        contentContainerStyle={[styles.content, { paddingTop }]}
        keyboardShouldPersistTaps="handled"
      >
        <TopBar title="" trailing={<IconButton icon="dots" accessibilityLabel="Assistant options" />} />
        <View style={styles.titleRow} accessibilityRole="header">
          <Text variant="sheetTitle">DHAN AI</Text>
          <Pill label="Preview" small />
        </View>
        <View style={styles.intro}>
          <View style={[styles.introIcon, { backgroundColor: c.primarySoft }]}>
            <Icon name="sparkle" size={iconSize.tab} color="primary" />
          </View>
          <Text variant="small" color="muted" align="center">
            Ask about your money in plain words. Answers use only what’s in DHAN.
          </Text>
        </View>
        {asked.map((id, i) => {
          const r = responses.find((x) => x.id === id);
          if (!r) return null;
          const last = i === asked.length - 1;
          return (
            <View key={id} style={styles.turn}>
              <ChatBubble role="user" text={r.question} />
              {(() => {
                const a = answerFor(r);
                if ((last && typing) || !a) return <TypingIndicator />;
                if ('error' in a) return <ChatBubble role="ai" text={a.error} />;
                return <ChatBubble role="ai" text={a.answer} stats={a.stats} />;
              })()}
            </View>
          );
        })}
        {suggestions.length ? (
          <View style={styles.suggest}>
            <SectionLabel>Try asking</SectionLabel>
            {suggestions.map((s) => (
              <Touchable
                key={s.id}
                disabled={typing}
                onPress={() => ask(s.id)}
                accessibilityLabel={`Ask: ${s.question}`}
                style={[styles.suggestion, { borderColor: c.line, backgroundColor: c.surface }]}
              >
                <Text variant="small" weight="medium">
                  {s.question}
                </Text>
              </Touchable>
            ))}
          </View>
        ) : null}
      </ScrollView>
      <View
        style={[
          styles.inputBar,
          { backgroundColor: c.bg, borderTopColor: c.line, paddingBottom: Math.max(insets.bottom, 30) },
        ]}
      >
        <View style={styles.inputRow}>
          <View style={[styles.input, { borderColor: c.line, backgroundColor: c.surface }]}>
            <TextInput
              accessibilityLabel="Ask DHAN AI"
              placeholder="Ask about your money…"
              placeholderTextColor={c.faint}
              selectionColor={c.primary}
              editable={false}
              style={[styles.inputText, { color: c.ink }]}
            />
            <IconButton icon="mic" variant="bare" accessibilityLabel="Voice input" />
          </View>
          <Touchable
            accessibilityLabel="Send"
            accessibilityHint="Typing questions is not available in this preview; tap a suggestion"
            style={[styles.send, { backgroundColor: c.primary }]}
          >
            <Icon name="send" size={iconSize.lg} color="onPrimary" strokeWidth={2} />
          </Touchable>
        </View>
        <Text variant="micro" weight="regular" color="muted" align="center">
          DHAN AI can make mistakes. Check important numbers.
        </Text>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  content: { paddingHorizontal: layout.gutter, paddingBottom: space[24], gap: space[18] },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[8],
    marginTop: -(size.touch + space[18]),
    marginLeft: size.touch + space[12],
    minHeight: size.touch,
  },
  intro: { alignItems: 'center', gap: space[8], paddingHorizontal: space[16] },
  introIcon: { width: 52, height: 52, borderRadius: 26, alignItems: 'center', justifyContent: 'center' },
  turn: { gap: space[18] },
  suggest: { gap: space[8] },
  suggestion: {
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderRadius: radius.field,
    paddingVertical: space[10],
    paddingHorizontal: space[14],
    minHeight: size.touch,
    justifyContent: 'center',
  },
  inputBar: { paddingTop: space[12], paddingHorizontal: space[16], borderTopWidth: 1, gap: space[8] },
  inputRow: { flexDirection: 'row', alignItems: 'center', gap: space[10] },
  input: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    height: 48,
    borderRadius: 24,
    borderWidth: 1,
    paddingLeft: space[16],
    paddingRight: space[4],
  },
  inputText: { flex: 1, fontFamily: fonts.regular, fontSize: textVariants.body.fontSize, padding: 0 },
  send: { width: 48, height: 48, borderRadius: 24, alignItems: 'center', justifyContent: 'center' },
});
