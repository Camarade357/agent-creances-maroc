# Agent Créances Maroc

Agent IA de gestion des créances pour PME marocaines.
Construit en public dans le cadre de Sprint A — Finance×IA.

## Stack
- Next.js 14 / TypeScript
- Supabase (base de données)
- Claude API (LLM)
- Vercel (déploiement)

## Architecture
Coordinator → Ingestion Agent → Aging Agent → Relance Agent → Réconciliation Agent → Forecast Agent → Report Agent

## Loi 69-21
Délai légal : 60j (sans convention) / 120j max (avec convention).
Déclaration trimestrielle DGI obligatoire pour CA > 2M MAD HT.

## Statut Sprint A
- [x] Semaine 1 : Setup + Ingestion Agent + Aging Agent
- [ ] Semaine 2-3 : Relance Agent
- [ ] Semaine 4-5 : Réconciliation + Coordinator
- [ ] Semaine 6-7 : Forecast + Report
- [ ] Semaine 8-9 : Dashboard
- [ ] Semaine 9 : Pilot onboarding

## Suivre le build
Newsletter Finance×IA : https://financexia.beehiiv.com/subscribe
