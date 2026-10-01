# DHAN — mobile app (iOS + Android)

*Dhan Hai Toh Done Hai.* A personal-finance app built from the frozen DHAN design canvas and implementation spec. It is frontend only: every number comes from a local mock database behind repository interfaces. There is no backend, network, real authentication or payments.

## Run it

Requirements:
- Node 20 or later.
- Xcode 16+ for iOS, or Android Studio with an emulator for Android.

```bash
npm install
npx expo install --fix     # aligns native packages with Expo SDK 54
npm run check              # typecheck + lint + project rules + tests
```

| Target | Command |
| --- | --- |
| Expo Go / dev menu | `npx expo start`, then press `i` for iOS or `a` for Android |
| iOS simulator (native build) | `npm run ios` (`expo run:ios`) |
| Android emulator (native build) | `npm run android` (`expo run:android`) |
| Physical device | `npx expo start`, then scan the QR code with Expo Go |

**Mock sign-in:** any email works, with the password `dhan-2026`. After a few wrong attempts the login screen shows its error state.

The mock clock is fixed at **30 Sep 2026**, so the seed data always matches the canvas.

## Architecture

```
Screen (features/*)  →  TanStack Query hook (data/queries)  →  Repository (data/repositories)  →  Mock DB (mock/)
```

- **Screens never import `mock/`.** `npm run rules` enforces this.
- **Mutations invalidate their queries.** One save updates Home, Activity, Budget, Accounts and Reports together.
- **Undo from toasts** goes through `data/queries/actions.ts`, because a toast can outlive the screen that showed it.
- **Swapping in a real backend:** rewrite the bodies of the `*Repo` objects in `data/repositories/index.ts` to call FastAPI. Keep the signatures; hooks and screens don't change.
- **Simulated latency, failure and offline** are controlled by `mock/config.ts`. Set `mockConfig.offline = true` to see the Reports offline-error state.

| Folder | Contents |
| --- | --- |
| `app/` | Expo Router routes. Groups: `(auth)`, `(app)`, `(tabs)`; plus modal and sheet routes |
| `features/` | Screens, grouped by area |
| `components/` | The 47-component library, the 73-icon `Icon`, charts, navigation, sheets and toast |
| `theme/` | Colour tokens (light and dark), spacing/radius/size/motion tokens, typography |
| `utils/` | Pure money logic: formatting, dates, summaries, budget, splits, goals, net worth, reports |
| `store/` | Zustand: prefs and session (persisted), drafts, filters, UI |
| `mock/` | Seed data and the in-memory database |

## Figures derived from the seed

None of these are hard-coded; `__tests__/invariants.test.ts` checks each one.

| Figure | Value |
| --- | --- |
| Net balance | ₹1,24,580 |
| September spent | ₹18,640 |
| September income | ₹43,000 |
| September net | +₹24,360 |
| Savings rate | 57% |
| Budget used | ₹17,100 of ₹24,000 |
| Splits | owed ₹5,700 · owe ₹1,000 · net ₹4,700 |
| Goals saved | ₹98,000 |
| Net worth | ₹2,18,680 |

## Tests

| Command | What it runs |
| --- | --- |
| `npm test` | Jest with jest-expo: invariants, repositories, utils, component tests (RNTL) and hook flow tests |
| `npm run test:logic` | Node-only runner for the logic suites; needs no `node_modules` |
| `npm run rules` | Project rules: no `any`; no raw colours, font sizes or font literals in UI; no mock imports from screens |
