# 07 — Scorecard de Valorisation Technique

**Projet** : KOREV Evidence  
**Date** : 3 avril 2026 (mise a jour : 17 avril 2026)  
**Methode** : notation fondee exclusivement sur les observations du depot  
**Note** : Scores recalcules au 17 avril 2026 pour refleter : corrections P0 (3 avril), nouveaux modules audit-proof (8 avril), et livrables P1/P2 (17 avril) : SECURITY.md, 5 ADR, GLOSSARY.md, diagrammes C4, 64 tests TDD documentation

---

## Grille de notation

Chaque dimension est notee sur 10 avec justification factuelle. Le score global est une moyenne ponderee refletant l'importance relative pour la valorisation.

---

## 1. Architecture — 6.5/10 (inchange)

**Poids valorisation : 15%**

| Force | Faiblesse |
|---|---|
| Separation claire agent/tools/extensions/api | Modules monolithiques (`settings.py` 2 225L, `agent.py` 1 144L) |
| Pipeline PRISM avec fail-closed et quorum | Duplications conceptuelles (2x `ArbiterConfig`, 3 chemins consensus) |
| Router deterministe avec contrats types | `helpers/` fourre-tout (181 fichiers, 77 155L) |
| Systeme d'extensions ordonne par hooks | Dual Docker non reconcilie |
| Persistence abstraite (JSON + Redis) | Etat global mutable (`_contexts`, `Memory.index`) |
| **Nouveaux modules bien structures** (replay_engine, human_review, dynamic_risk_register, strategic_charts) | |

**Justification** : L'architecture a de l'intention et des patterns professionnels. Les nouveaux modules (avril 2026) sont bien structures. Mais la dette structurelle (monolithes, duplications) subsiste. Un 8+ necessiterait le scindage des monolithes et l'unification du consensus.

---

## 2. Lisibilite — 6/10

**Poids valorisation : 10%**

| Force | Faiblesse |
|---|---|
| Nommage coherent (snake_case, PascalCase classes) | Melange FR/EN (bannieres FR, docstrings EN) |
| Docstrings presentes sur les modules critiques | Code mort/commente (browser.py 336L, blocs dans initialize.py, files.py) |
| Commentaires expliquant les gardes non-evidentes | Emojis dans certains logs |
| App factory documentee dans run_ui.py | Import duplique dans models.py |
| Extensions nommees par convention (_10_, _20_) | Contraste entre modules bien documentes et modules opaques |

**Justification** : Un developpeur senior Python peut naviguer le code, mais la charge cognitive des modules volumineux et le bruit du code mort reduisent l'efficacite. Le melange linguistique, bien que comprehensible, n'est pas professionnel pour un contexte international.

---

## 3. Maintenabilite — 6.5/10 (precedemment 6.0)

**Poids valorisation : 15%**

| Force | Faiblesse |
|---|---|
| Extension hooks permettent la modification sans toucher au noyau | `Agent.monologue()` complexite cyclomatique ~25-40 |
| Contrats types pour le consensus et le routage | Connaissance implicite du contrat d'extensions (attenuee par ADR-005) |
| Persistence abstraite | ~~`asyncio.run()` crash~~ corrige dans le scheduler |
| Profiles d'agents separent la configuration | Bus factor = 1 (pas de CODEOWNERS, pas de contributor guide effectif) |
| Guide onboarding v7.1 (1 196 lignes, avril 2026) | |
| Reference documentaire a 3 910 tests collectes avec parametrisation pour la regression | |
| **5 ADR documentant les decisions architecturales** (nouveau 17 avril) | |
| **Glossaire technique definissant les termes proprietaires** (nouveau 17 avril) | |
| **Diagrammes C4 a 3 niveaux** (nouveau 17 avril) | |

**Justification** : Les ADR (5 decisions documentees), le glossaire technique et les diagrammes C4 reduisent significativement la charge cognitive pour un nouveau mainteneur. La connaissance implicite des contrats d'extensions est partiellement explicite via ADR-005. Score passe de 6.0 a 6.5. Un 7+ necessiterait le scindage des monolithes et un contributor guide effectif.

---

## 4. Securite percue — 7.5/10 (precedemment 7.0)

**Poids valorisation : 15%**

| Force | Faiblesse |
|---|---|
| Argon2id pour les mots de passe | ~~Cle HMAC par defaut~~ ✅ RuntimeError si absente |
| Rate limiting Redis + memoire | Mode sans auth quand config absente (ELEVEE — non corrige) |
| Path safety, upload validation, shell safety | ~~Mot de passe en clair dans logs~~ ✅ Placeholder generique |
| Autorisation multi-tenant par principal | ~~RBAC audit_reports incoherent~~ ✅ Aligne avec politique |
| Security audit logging | Masquage secrets fail-open (`except: pass`) |
| CSRF sur API mutantes | Browser agent `disable_security=True` |
| Isolation workspace | Comparaison cle API non constante |
| Specification Gherkin dans security/__init__.py | ~~Pas de SECURITY.md~~ ✅ Cree le 17 avril 2026 |
| **4 failles P0 corrigees** | |
| **SECURITY.md** : politique de divulgation, perimetre, pratiques crypto, architecture secu (nouveau 17 avril) | |

**Justification** : SECURITY.md couvre la politique de divulgation responsable, les pratiques cryptographiques (Argon2id, HMAC-SHA256, RSA), le rate limiting, le RBAC multi-tenant et les limites connues. Ce document est un signal de maturite attendu par tout evaluateur. Score passe de 7.0 a 7.5. Un 8+ necessiterait l'activation de l'auth par defaut et le fail-closed sur le masquage.

---

## 5. Testabilite — 7.5/10 (precedemment 7.0)

**Poids valorisation : 10%**

| Force | Faiblesse |
|---|---|
| Reference documentaire a 3 910 tests collectes avec parametrisation (~180 fichiers ; audit initial : ~3 846 tests / 179 fichiers) | Suite etendue non-bloquante en CI |
| Harness de simulation (FakeLLMProvider, FakeMCPHandler) | Couverture globale non mesuree |
| Guard reseau LLM (bloque les appels reels par defaut) | ~50 endpoints API sans test dedie |
| Tests de securite avec seuil en CI (90%) | |
| Tests de proprietes et invariants | |
| Redis multi-worker proof | |
| Golden tests pour le legal pipeline | |
| Tests e2e audit-proof (replay, human review, risk register) | |
| Tests hostile hardening (203 lignes dedies) | |

**Justification** : Le volume de tests a augmente de ~39% (2 770 → 3 846). Les nouveaux tests couvrent les modules critiques (audit-proof, hostile hardening). Le 7.5 au lieu de 8+ est du a la non-bloquance de la suite etendue et a l'absence de couverture mesuree globalement.

---

## 6. Documentation — 7.0/10 (precedemment 5.5)

**Poids valorisation : 10%**

| Force | Faiblesse |
|---|---|
| ~245+ fichiers markdown | Pas de schema de donnees |
| Guide onboarding v7.1 detaille (1 196 lignes) — mis a jour avril 2026 | Pas d'API reference |
| Feuille de route conformite a jour (1 893L) | Melange FR/EN sans logique |
| Rapport de valorisation technique existant et mis a jour | Doublons (tmp/uploads/ vs docs/) |
| Changelog audit structure | |
| Guide deploiement entreprise (1 385L) | |
| README par sous-module (router, contract_drafting) | |
| Templates de rapports Evidence | |
| ~~Pas d'ADR~~ ✅ **5 ADR** (PRISM, router, Evidence, LiteLLM, extensions) — nouveau 17 avril | |
| ~~Pas de SECURITY.md~~ ✅ **SECURITY.md** a la racine — nouveau 17 avril | |
| **GLOSSARY.md** (30+ termes proprietaires definis) — nouveau 17 avril | |
| **Diagrammes C4** (contexte, containers, composants + sequence) en Mermaid — nouveau 17 avril | |
| **Benchmark comparables de valorisation** (section 6bis) — nouveau 17 avril | |
| **64 tests TDD** validant la structure et le contenu documentaire — nouveau 17 avril | |

**Justification** : Les 4 lacunes documentaires majeures identifiees dans l'audit (ADR, SECURITY.md, glossaire, diagrammes) sont desormais comblees. 5 ADR documentent les decisions architecturales. Le glossaire definit les termes proprietaires. Les diagrammes C4 en Mermaid rendent l'architecture explicite a 3 niveaux de zoom. Des tests TDD verifient la structure. Score passe de 5.5 a 7.0. Un 8+ necessiterait un schema de donnees, une API reference et l'elimination des doublons.

---

## 7. Auditabilite — 8.5/10 (precedemment 7.5)

**Poids valorisation : 10%**

| Force | Faiblesse |
|---|---|
| Framework Evidence : 10 blocs canoniques de rapport | RSA optionnel, dependant de la configuration |
| Integrite cryptographique (SHA-256 + HMAC/RSA) — ✅ cle HMAC obligatoire | Pas de stockage WORM pour les traces |
| SessionEnvelope avec metadonnees completes | Auto-evaluation sans validation externe |
| ComplianceGrid (Art. 9, 13, 14, 17 AI Act + RGPD 30) | |
| RiskRegister et ProcessingRegister | |
| Feuille de route conformite tracee par session | |
| Security audit logging structure | |
| Transparence narrative (to_safe_narrative) | |
| **Replay Engine** — rejeu deterministe de sessions (nouveau avril 2026) | |
| **Human Review Workflow** — revue humaine pour decisions critiques (nouveau avril 2026) | |
| **Dynamic Risk Register** — scoring de risques temps reel (nouveau avril 2026) | |

**Justification** : C'est le point fort differenciateur du projet. Le framework Evidence + les 3 nouveaux modules audit-proof (replay, human review, risk register) constituent un actif IP exceptionnel. La cle HMAC est desormais obligatoire. Le 8.5 au lieu de 9+ est du a l'absence de validation externe et de stockage WORM.

---

## 8. Industrialisation — 6.0/10 (precedemment 5.5)

**Poids valorisation : 10%**

| Force | Faiblesse |
|---|---|
| Docker Compose production fonctionnel | Pas de build Docker en CI |
| Caddy reverse proxy avec TLS auto | Pas de SAST/scanning dependances |
| Healthcheck Docker (180s start, 30s interval) | Scripts deploy (install/upgrade) incoherents avec la config |
| Log rotation Docker configuree | Pas de monitoring/alerting dans le repo |
| Non-root user dans le container | Deux .env.example |
| Volumes nommes avec labels de backup | Deploiement manuel (pas de CD) |
| Scripts de rollback documentes | |
| PRISM PDF engine reecrit (WeasyPrint + ReportLab fallback) | |
| Docker Playwright/Chromium ameliore pour Debian trixie | |
| Polices professionnelles (Inter, Playfair Display) integrees | |

**Justification** : Le deploiement fonctionne et a ete ameliore (Docker Playwright, polices, PDF engine). Le score passe de 5.5 a 6.0. Un 7+ necessiterait un build Docker en CI et du SAST.

---

## 9. Reprise par tiers — 6.5/10 (precedemment 5.0)

**Poids valorisation : 5%**

| Force | Faiblesse |
|---|---|
| Python standard (Flask, dataclasses, typing) | Bus factor = 1 |
| Structure repo lisible au premier niveau | `helpers/` opaque (181 fichiers) — attenue par C4 |
| Guide onboarding v7.1 detaille (1 196 lignes) — ameliore | Pas de CODEOWNERS |
| Reference documentaire a 3 910 tests collectes + 64 tests doc pour la regression | Pas de schema de donnees |
| requirements.txt avec versions pinees | ~1.5-2 semaines d'onboarding minimum estimes |
| Replay engine permet de comprendre le flux d'execution | |
| ~~Pas d'ADR~~ ✅ **5 ADR** documentant les decisions architecturales — nouveau 17 avril | |
| **GLOSSARY.md** (30+ termes proprietaires) — nouveau 17 avril | |
| **Diagrammes C4** (3 niveaux + sequence) — nouveau 17 avril | |
| **SECURITY.md** — nouveau 17 avril | |

**Justification** : Les ADR (5 decisions), le glossaire, les diagrammes C4 et le SECURITY.md reduisent significativement le temps d'onboarding et la dependance a la connaissance implicite. Le temps d'onboarding estime passe de 2-3 semaines a ~1.5-2 semaines. Score passe de 5.0 a 6.5. Un 7+ necessiterait CODEOWNERS, un schema de donnees et un contributor guide effectif.

---

## 10. Credibilite de valorisation — 7.0/10 (precedemment 6.0)

**Poids valorisation : (meta)**

| Force | Faiblesse |
|---|---|
| PRISM est un differenciateur reel | ~~Contradiction de licence~~ ✅ Corrigee |
| Evidence est un framework innovant | ~~Failles secu critiques~~ ✅ P0 corriges |
| Legal pipeline est un actif vertical | Documentation non structuree pour tiers |
| Volume de code significatif (186 865L Python ; 262 commits Amine au 8 avril, 267 commits / +221 481 insertions au 24 avril 2026) | Pas de metriques d'usage reel |
| Conformite AI Act/RGPD demonstrable | Auto-evaluation (atenuee par audit-proof pipeline) |
| Feuille de route tracee et complete | Dependance apporteur / inventeur |
| Pipeline audit-proof (replay, human review, risk register) | |
| Reference documentaire a 3 910 tests collectes avec parametrisation | |

---

## Score global

| Dimension | Score initial (3 avr.) | Score post-P0 (17 avr.) | Score actuel (17 avr., post-P1/P2) | Poids | Contribution |
|---|---|---|---|---|---|
| Architecture | 6.5 | 6.5 | 6.5 | 15% | 0.975 |
| Lisibilite | 6.0 | 6.0 | 6.0 | 10% | 0.600 |
| Maintenabilite | 5.5 | 6.0 | **6.5** | 15% | **0.975** |
| Securite percue | 5.0 | 7.0 | **7.5** | 15% | **1.125** |
| Testabilite | 7.0 | 7.5 | 7.5 | 10% | 0.750 |
| Documentation | 5.0 | 5.5 | **7.0** | 10% | **0.700** |
| Auditabilite | 7.5 | 8.5 | 8.5 | 10% | 0.850 |
| Industrialisation | 5.5 | 6.0 | 6.0 | 10% | 0.600 |
| Reprise par tiers | 4.5 | 5.0 | **6.5** | 5% | **0.325** |
| **TOTAL** | **58.75/100** | **65.25/100** | | **100%** | **6.900 → 69.00/100** |

---

## Positionnement

```
0        20        40        60        80        100
├─────────┼─────────┼─────────┼─────────┼─────────┤
                              ×    ▲    ●
                              │    │    │
                     Initial  P0  P1/P2 partiel
                     (58.75) (65.25) (69.00)
                                        │
      Prototype ──── Produit en structuration ──── Actif industriel
      avance              ▲ base valorisable          premium
```

**Verdict** : KOREV Evidence est passe de 58.75 a 65.25/100 (corrections P0) puis a 69.00/100 (SECURITY.md, 5 ADR, GLOSSARY.md, diagrammes C4). Le projet est desormais solidement dans la zone "base technique valorisable". La poursuite du P1+P2 restant (tests bloquants, couverture, Docker CI, auth defaut, scindage settings) pourrait le faire passer a ~73-76/100.

---

## Score post-remediation estime (si P1 + P2 restants executes)

| Dimension | Actuel (17 avr.) | Apres P1+P2 complets | Delta |
|---|---|---|---|
| Architecture | 6.5 | 7.5 | +1.0 |
| Lisibilite | 6.0 | 7.0 | +1.0 |
| Maintenabilite | 6.5 | 7.5 | +1.0 |
| Securite percue | 7.5 | 8.5 | +1.0 |
| Testabilite | 7.5 | 8.5 | +1.0 |
| Documentation | 7.0 | 8.0 | +1.0 |
| Auditabilite | 8.5 | 9.0 | +0.5 |
| Industrialisation | 6.0 | 7.5 | +1.5 |
| Reprise par tiers | 6.5 | 7.5 | +1.0 |
| **TOTAL** | **69.00** | **~76/100** | **+~7** |

### Comparaison avec l'etat initial de l'audit (3 avril 2026)

| Etape | Score | Decote realiste estimee |
|---|---|---|
| Audit initial (3 avril 2026) | 58.75/100 | 25-40% |
| Apres corrections P0 | 65.25/100 | 15-25% |
| **Apres P1/P2 partiel (actuel — SECURITY.md, ADR, glossaire, C4)** | **69.00/100** | **12-20%** |
| Apres P1+P2 complets (estime) | ~76/100 | 8-12% |
