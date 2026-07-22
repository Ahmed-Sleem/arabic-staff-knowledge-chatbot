# Topic 5 — Frontend (Next.js, GPR-styled)

**Status:** Phase 2 — Deep Dive (in progress)
**Last update:** 2026-07-10

---

## Open questions

1. **Next.js version**: 15 (App Router) confirmed by modern GPR design system.
2. **GPR design system adaptation**:
   - The GPR DS is for a broader IDE/chat product. We need to extract just the chat surface, tokens, and primitives we need.
   - Tokens: colors, spacing, radii, control heights, icon sizes, typography, motion, z-index — apply all.
   - Primitives: `<Button>`, `<IconButton>`, `<Input>`, `<Field>`, `<Search>`, `<RowAction>`, `<Panel>`, `<SidePanel>`, `<Dialog>`, `<Tooltip>`, `<Kbd>`, etc.
3. **Arabic RTL**:
   - Set `<html dir="rtl" lang="ar">`.
   - Use an Arabic-friendly font that supports Latin too (since technical terms like "KPI", "PMO" appear in Arabic text). Candidates:
     - IBM Plex Sans Arabic
     - Tajawal
     - Noto Sans Arabic
     - GE SS Two
     - Cairo (Google Fonts)
   - Number handling — Arabic-Indic digits vs Latin digits (PRD doesn't specify, default to Latin digits for technical clarity).
4. **Chat surface** (per GPR design philosophy):
   - Conversation thread (scrollable panel)
   - Message bubble (user / assistant)
   - Markdown rendering (with Arabic-safe rules, RTL lists)
   - Citation chip (showing "section X.Y, page Z")
   - Composer (textarea + send button)
   - Streaming response handling (SSE / fetch stream)
5. **Admin surface**:
   - Doc upload (drag-drop)
   - Doc list (name, version, status, actions: re-index, disable, test)
   - Test question runner (chat against candidate index)
   - Logs dashboard (table + filters + top-asked chart)
6. **Auth surface**: login, register, OTP request/verify.
7. **Mobile**:
   - Per `DEVELOPMENT_REQUIREMENTS.md §6`, mobile is chat/input-output only.
   - GPR DS has mobile rules — apply min 44x44 tap targets, safe-area-inset-bottom.
8. **i18n**: Arabic only for MVP. Per GPR §7.5, all user-facing copy still goes through `useT()` for future-proofing.
9. **State management**: zustand per GPR rule.
10. **Data fetching**: TanStack Query (React Query) for server state.
11. **Styling**: Tailwind v4 + GPR `@theme inline` tokens.

---

## Findings (append below)


## Findings — Next.js + TanStack Query + SSE streaming

### Source 1 — fragmentedthought.com "React Query and Server Side Events" (May 2025)
URL: https://fragmentedthought.com/blog/2025/react-query-caching-with-server-side-events
- Pattern: use TanStack Query as a caching layer in front of an EventSource (SSE).
- Custom `useConversationState` hook wraps the EventSource and writes state into the query cache.
- Uses `last-event-id` header for resumption.
- AbortController tied to component lifecycle.
- Key gotcha: `refetchOnWindowFocus: false` or you get duplicates.

### Source 2 — Reddit r/nextjs "Next.js + Express: Is TanStack Query overkill" (Dec 2025)
- "For client side data fetching, TanStack Query is always preferred over rolling your own queries with useEffect."
- "Use next.js for SSR fetch and store it as initialData in tanstack query and that's it. You have magic."
- Confirmed pattern: TanStack Query is the right tool for client state in a Next.js app with a separate FastAPI backend.

### Source 3 — TanStack Query docs "Advanced Server Rendering" (Sep 2023)
- `staleTime: 60 * 1000` as a sane default for SSR.
- `QueryClientProvider` must be wrapped in a `'use client'` component in Next.js App Router.
- For streaming with prefetching: use `@tanstack/react-query-next-experimental`.

### Source 4 — Medium "3 TanStack Query Features That Transform Production React Apps" (Aug 2025)
- `broadcastQueryClient` (experimental) syncs cache across tabs.
- `staleTime: 60 * 1000` is the default for streaming AI responses.
- Security: don't broadcast sensitive data (auth tokens).

### Implication for our project
- **Stack decision:** Next.js 15 App Router + TanStack Query v5 + native `EventSource` (no extra dep).
- **Why EventSource and not fetch streams:** simpler, auto-reconnect, last-event-id support out of the box. The fragmentedthought.com pattern is exactly what we need.
- **Why not React Query streaming helper:** it doesn't exist as a separate package. The pattern is to write a small custom hook.
- **SSR considerations:** chat page is heavily client-side (no SEO value), so we can mark it `'use client'`. Login and landing can SSR.
- **TanStack Query setup:**
  - `staleTime: 60_000` for list queries.
  - `staleTime: Infinity` for the current conversation.
  - No automatic refetch on focus for the chat state.

## Findings — Arabic RTL typography (web)

### Source 1 — voxire.com "Arabic RTL Typography for Web Design: 2026 Guide" (Jun 2026)
URL: https://voxire.com/blog/arabic-rtl-typography-web-design-2026/
- **Use a real Arabic webfont, not the system default.** Leaders in 2026: IBM Plex Sans Arabic, Cairo, Tajawal, Noto Sans Arabic, Rubik.
- **Line height: 1.7-1.85 for body, 1.3-1.4 for headings.** Latin defaults (1.5) crash Arabic letters.
- **Letter-spacing: 0 ALWAYS for Arabic.** Tracking breaks ligatures.
- **Use dual-script fonts** (IBM Plex Sans Arabic) for mixed content — the Latin glyphs are designed to match the Arabic glyphs.
- **Arabic body text: 15-17px typically.** IBM Plex Sans Arabic reads well at 16-17px.
- **Labels above the field, not to the side.** (Right-of-field is the RTL equivalent of "to the left of", which is visually confusing.)
- **Input: `dir="rtl"` + `text-align: start` (not "right").**
- **Numerals: Western Arabic (0-9) is the default in KSA, UAE, Lebanon in 2026.** Eastern Arabic (٠-٩) feels traditional but causes friction in forms and prices.
- **Use logical CSS properties:** `margin-inline-start`, `padding-inline-end` (not `margin-left`, `padding-right`).

### Source 2 — bycomsolutions.com "Arabic RTL Web Design Best Practices" (Jan 2026)
URL: https://bycomsolutions.com/blog/arabic-rtl-web-design-best-practices/
- **Saudi websites typically need both Arabic and English.** Bilingual is the norm.
- Font stack: `'IBM Plex Sans Arabic', 'Noto Sans Arabic', 'Segoe UI', Tahoma, sans-serif`.
- Recommended: Cairo for headings, Tajawal for body, or IBM Plex Sans Arabic for corporate/tech brand.
- **Avoid bold overuse.** Arabic bold can become harder to read due to connected letter forms.
- **Test with real Arabic content, not lorem ipsum.** Lorem ipsum doesn't reveal Arabic typography issues.

### Source 3 — github.com/umami-software/umami #3740 (Nov 2025)
URL: https://github.com/umami-software/umami/issues/3740
- Issue: Inter font displays poorly for Arabic. Recommendation: use `next/font/google` with `Noto_Sans_Arabic` for Arabic script and `Inter` for Latin.
- Pattern: language-aware font selection via `:lang(ar)` selector.
- Implementation: `import { Noto_Sans_Arabic } from 'next/font/google'` with `subsets: ['arabic']`.

### Source 4 — cloudtopia.net "Best Website Design Practices for RTL Arabic Layouts in 2026" (Jun 2026)
URL: https://cloudtopia.net/articles/best-website-design-practices-for-rtl-arabic-layouts-in-2026
- Confirmed: KSA uses Western Arabic numerals predominantly in digital/business.
- Body font size for Arabic: 18-20px (vs 15-16 for English).
- **Line height 1.6-1.8 minimum** for Arabic body.
- Letter spacing = 0 always.
- Use Google Fonts with `display=swap` to avoid FOIT.

### Implication for our project
- **Font choice (locked):** **IBM Plex Sans Arabic** for body. It's professional, corporate, has matching Latin glyphs in the same family, and is widely used in Saudi/Arab corporate UIs. Fallback: `'Noto Sans Arabic', 'Segoe UI', Tahoma, sans-serif`.
- **Body text size:** 16-17px in IBM Plex Sans Arabic, with line-height 1.75.
- **Numerals:** Western Arabic (0-9) — matches KSA convention.
- **Implementation:** Use `next/font/google` to load IBM Plex Sans Arabic. Apply via `:lang(ar)` selector or by setting `<html lang="ar" dir="rtl">` and using the font as the default.
- **CSS strategy:** Use logical properties throughout (`margin-inline-start`, `padding-inline-end`). The GPR design system uses Tailwind v4 which supports this.
- **GPR design system adaptation:**
  - Apply GPR's color/spacing/control tokens unchanged.
  - Replace Inter (the GPR default) with IBM Plex Sans Arabic for Arabic script, fall back to Inter for Latin.
  - Adjust line-heights globally for Arabic (`leading-1.75` body, `leading-1.4` headings) — add as GPR motion tokens.
  - Set `<html dir="rtl" lang="ar">` in the root layout.
  - Use logical properties in the GPR primitives (`ms-2` instead of `ml-2`, `me-2` instead of `mr-2` — Tailwind v4 has these).

