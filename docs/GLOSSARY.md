# Glossaire technique — KOREV Evidence

Ce document definit les termes proprietaires et les concepts specifiques a KOREV Evidence. Il s'adresse aux developpeurs, auditeurs et evaluateurs techniques.

---

## A — Architecture et orchestration

**Agent (Evidence)** — Unite d'orchestration qui execute un cycle monologue-action. Chaque agent est configure par un profil (`agents/<nom>/`) et enrichi par des extensions (cf. Extension).

**Agent Loop (boucle d'agent)** — Cycle iteratif dans lequel l'agent recoit un message, genere un raisonnement (monologue), execute des outils, et produit une reponse. La boucle est instrumentee par 24 hooks d'extension.

**ArbiterCaller** — Composant de `python/helpers/consensus_arbiter.py` responsable de l'appel aux modeles LLM participant au consensus. Configure les parametres de chaque arbitre et gere les timeouts et erreurs.

**ConsensusConfig** — Configuration du systeme de consensus : nombre d'arbitres, quorum, timeout, modeles a interroger. Charge par `load_consensus_config()`.

**ConsensusManager** — Gestionnaire central du protocole de consensus (`python/helpers/consensus_manager.py`). Orchestre les votes, calcule le quorum, produit un `ConsensusResult` avec `VoteCount` et `DecisionType`.

**ConsensusEngine** — Point d'entree unique du systeme de consensus (`python/consensus/engine.py`). Expose `run_consensus()`. Toute decision de consensus passe obligatoirement par cette interface.

## C — Conformite et audit

**ComplianceGrid** — Grille d'auto-evaluation de conformite mappee sur les articles de l'AI Act (articles 9, 13, 14, 17) et du RGPD (article 30). Generee dans les rapports Evidence.

**ConfidenceBadge** — Label de confiance attribue a chaque affirmation dans un rapport : `VERIFIED` (preuves reproductibles), `PARTIAL` (preuves partielles), `UNVERIFIED` (aucune preuve), `FAIL_CLOSED` (criticite elevee sans preuve, declenchant un refus).

## D — Decision et routage

**DynamicRiskRegister** (module `python/helpers/dynamic_risk_register.py`) — Registre de risques dynamique. Expose `class SessionRiskAssessment` (evaluation par session, 6 facteurs ponderes, classification LOW/MEDIUM/HIGH/CRITICAL) et `class SystemRiskDashboard` (tableau de bord agrege). Invoque par l'extension `monologue_end/_36_risk_assessment.py`.

## E — Evidence (framework)

**Evidence** — Nom du framework de reporting et d'audit natif de KOREV. Designe a la fois la plateforme et le module central (`python/helpers/evidence.py`). Le terme « Evidence » fait reference a la notion de preuve au sens juridique : chaque decision produite est tracable, signee et verifiable.

**Evidence-native (rapport)** — Rapport genere par le framework Evidence suivant une structure normalisee en 10 blocs canoniques. Produit par `python/helpers/reporting/evidence_native.py`.

**Extension** — Module Python qui s'inscrit dans un hook du cycle de vie de l'agent pour en modifier le comportement. Herite de la classe `Extension` et implemente `async def execute()`. Nomme `_<ordre>_<description>.py` pour garantir un ordre d'execution deterministe.

## F — Fiabilite

**fail-closed** — Politique de securite selon laquelle, en cas d'erreur ou d'indisponibilite, le systeme refuse d'agir plutot que de produire un resultat potentiellement incorrect. Appliquee au consensus (pas de reponse sans quorum), au rate limiting configurable, et aux decisions de criticite elevee.

## H — Hooks et cycle de vie

**Hook (cycle de vie)** — Point d'ancrage dans le cycle de l'agent ou des extensions peuvent etre injectees. 24 hooks sont definis : `agent_init`, `system_prompt`, `monologue_start`, `monologue_end`, `message_loop_start`, `message_loop_end`, `message_loop_prompts_before`, `message_loop_prompts_after`, `before_main_llm_call`, `response_stream`, `response_stream_chunk`, `response_stream_end`, `reasoning_stream`, `reasoning_stream_chunk`, `reasoning_stream_end`, `tool_execute_before`, `tool_execute_after`, `hist_add_before`, `hist_add_tool_result`, `legal_safe_mode`, `strategic_validation`, `user_message_ui`, `util_model_call_before`, `error_format`.

**HumanReview** (module `python/helpers/human_review.py`) — Workflow de revue humaine des decisions critiques. Expose `class ReviewRequest` (demande de validation avec etats PENDING_REVIEW / APPROVED / REJECTED) et `class ReviewDecision` (decision d'un reviewer : identifiant, timestamp, justification).

## I — Integrite

**IntegrityBlock** — Structure de donnees (`python/helpers/integrity_block.py`) qui encapsule la signature cryptographique d'un rapport d'audit. Contient : hashes SHA-256 de la requete, de la reponse et du document ; signature HMAC-SHA256 ou RSA-PSS-SHA256 ; horodatage ; identifiant de cle.

## L — Legal-Safe

**Legal-Safe (mode)** — Mode de fonctionnement specialise pour les requetes juridiques, implemente par l'extension `legal_safe_mode/_10_legal_safe_integration.py`. Active des garde-fous supplementaires : disclaimers, verification de jurisdiction, detection de conseil juridique personnalise, interdiction de certaines conclusions.

## M — MCP

**MCP (Model Context Protocol)** — Protocole standardise d'echange de contexte entre l'agent et des serveurs externes. Evidence integre des serveurs MCP pour etendre les capacites de l'agent (outils, ressources, donnees).

## P — Profils et pipelines

**Profil d'agent** — Configuration complete d'un agent stockee dans `agents/<nom>/`. Contient des prompts, des contextes, des outils et des extensions specifiques au domaine. 12 profils existants : `_example` (template), `default`, `developer`, `finance`, `hacker`, `legal_drafting_guarded`, `legal_safe`, `marketing`, `medical`, `multitask`, `researcher`, `sales`.

**PRISM** — Nom historique du systeme de consensus multi-arbitres de KOREV Evidence. Le nom provient du projet predecesseur (le repo GitHub s'appelle encore `PRISM-Oracle`). Designe l'ensemble du pipeline : `ConsensusEngine`, `ConsensusManager`, `ArbiterCaller`, contrats et politiques.

## R — Reporting et rejeu

**ReplayEngine** (module `python/helpers/replay_engine.py`) — Module de rejeu deterministe. Expose `capture_snapshot()` pour sauvegarder l'etat d'une session et `class ReplayOutcome` pour le resultat d'un rejeu. Invoque par l'extension `monologue_end/_35_replay_snapshot.py` a chaque fin de monologue.

**RouteDecision** — Objet type retourne par le router deterministe (`python/helpers/router/routing_contract.py`). Contient les intents detectes, le verdict de routage, le `route_id` (hash SHA-256), et les metriques associees.

**RouteIntent** — Intent atomique detecte par le router : un domaine (ex: `finance`, `legal_safe`, `medical`) et un score de confiance. Combine dans `RouteDecision` pour former un multi-intent.

## S — Sessions et securite

**SessionEnvelope** — Conteneur de metadonnees pour chaque session de traitement (`python/helpers/session_envelope.py`). Format : `KRV-SES-YYYYMMDD-XXXXXXX`. Lie un rapport d'audit a une session specifique et fournit les metadonnees techniques (version, environnement, horodatage).

**SecurityError** — Exception levee par le module de securite (`python/security/path_safety.py`) en cas de violation de politique : traversee de repertoire, chemin hors perimetre, lien symbolique non autorise.

**StrategicEnforcement** — Systeme de validation strategique (`python/extensions/strategic_validation/`) qui verifie que les reponses de l'agent respectent les politiques definies (limites de mandat, coherence avec le profil, absence de recommandations interdites).

## V — Validation et votes

**VoteCount** — Structure de comptage des votes dans un consensus : total, favorables, defavorables, abstentions, erreurs. Utilisee pour calculer le quorum.

**VoteType** (`VoteVerdictEnum`) — Type de vote d'un arbitre dans le consensus : `APPROVE`, `REJECT`, `ABSTAIN`. Un arbitre indisponible ou en timeout retourne `None` (pas de vote, distinct d'un `ABSTAIN` explicite).

---

*Document genere le 17 avril 2026. Version 1.0.*
